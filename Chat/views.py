import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt  
import os
import re
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain_core.prompts import PromptTemplate
from langchain.chains.question_answering import load_qa_chain
from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import firebase_admin
from firebase_admin import credentials, storage
from pathlib import Path as p
from rest_framework.response import Response
from .datastore_service import fetch_entities, update_entity, create_user, fetch_user, check_user, add_entity
import hashlib
import jwt
import datetime
from jwt import ExpiredSignatureError, InvalidTokenError

os.environ['google_api_key'] = 'AIzaSyD5hkSzLGV8rLVKk5g6qW-nWPufkn0UT98'
APPEND_SLASH = False

# Configure Google Generative AI
genai.configure(api_key=os.environ.get('google_api_key'))

secret_key=os.environ.get('secret_key')
def validate_token(token):
    try:
        decoded_jwt=jwt.decode(token, "secret", algorithms=["HS256"])
        return decoded_jwt, None
    except ExpiredSignatureError:
        return None, 'Token has expired'
    except InvalidTokenError:
        return None, 'Invalid token'
    
@csrf_exempt
def chat_with_documents(request):
    if request.method == 'POST':
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return JsonResponse({'error': 'Authorization header missing'}, status=401)
        
        token = auth_header.split(' ')[1]
        decoded, error = validate_token(token)
        if error:
            return JsonResponse({'error': error}, status=401)
        # Extract data from the request
        data = json.loads(request.body)

        bot_id = data.get('bot_id')
        question = data.get('question')
        entities = fetch_entities('chatbotdata', bot_id.lower())
        context = entities[0]['data']

        # Process the question with the extracted context
        # prompt_template = """Trả lời câu hỏi với ngữ cảnh được cho. Nếu câu trả lời không có trong ngữ cảnh, trả về "Chưa đủ dữ liệu để trả lời" \n\n
        #             Ngữ cảnh: \n {context}?\n
        #             Câu hỏi: \n {question} \n
        #             Câu trả lời:
        #           """
        prompt_template = """Answer the question as precise as possible using the provided context. If the answer is
                    not contained in the context, say "Chưa đủ dữ liệu để trả lời" \n\n
                    Context: \n {context}?\n
                    Question: \n {question} \n
                    Answer:
                  """

        prompt = PromptTemplate(
            template=prompt_template, input_variables=["context", "question"]
        )
        model = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3)
        stuff_chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)

        """### RAG Pipeline: Embedding + LLM"""
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=0)
        texts = text_splitter.split_text(context)

        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

        vector_index = Chroma.from_texts(texts, embeddings).as_retriever()
        docs = vector_index.get_relevant_documents(question)

        stuff_answer = stuff_chain(
            {"input_documents": docs, "question": question}, return_only_outputs=True
        )
        
        # Return the response
        return JsonResponse({"answer": stuff_answer})
    else:
        return JsonResponse({"error": "Only POST requests are allowed"})


@csrf_exempt
def update_data(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        bot_id = data.get('bot_id').upper()
        context =''

        if not firebase_admin._apps:
            cred = credentials.Certificate("complete-verve-420306-firebase-adminsdk-px8jn-d8c65cdb28.json")
            default_app = firebase_admin.initialize_app(cred, {'storageBucket': 'complete-verve-420306.appspot.com'})
            bucket = storage.bucket(app=default_app, name='complete-verve-420306.appspot.com')

            blobs = bucket.list_blobs(prefix=str(bot_id)+'/')
            data_folder = p.cwd() / str("data/"+str(bot_id))
            p(data_folder).mkdir(parents=True, exist_ok=True)
            for blob in blobs:
                destination_file =p(blob.name)
                blob.download_to_filename("data/"+bot_id+'/'+re.sub(r'[^\w_. -]', '_', str(destination_file)))

            pdf_search = data_folder.glob("*.pdf")
        # convert the glob generator out put to list
            pdf_files = pdf_files = [str(file.absolute()) for file in pdf_search]
            for pdf in pdf_files:
            # Extract text from the PDF
                pdf_loader = PyPDFLoader(pdf)
                pages = pdf_loader.load_and_split()
                context = context+"\n\n".join(str(p.page_content) for p in pages)
        
            update_entity(bot_id.lower(), context)
            firebase_admin.delete_app(default_app)
        return JsonResponse({"bot_id": str(bot_id)+'/', "context":context})
    else:
        return JsonResponse({"error": "Only POST requests are allowed"})

@csrf_exempt
def register(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        email = data.get('email')
        username = data.get('username') 
        password = data.get('password')
        phone = data.get('phone')
        data_fields = ['username', 'password', 'phone', 'email']

        email_regex = r"^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$"  

        # Combine field checks and email validation using list comprehension and 'all'
        if not all(data.get(field) and (field != 'email' or re.match(email_regex, email)) for field in data_fields):
            return JsonResponse({'error': 'Some fields are missing or invalid'}, status=400)


        data = {
            'email': email,
        }
        result=check_user(data)
        
        if result:
            return JsonResponse({"error": 'This email is already existed'}, status=409)
        else:
            salt = "5gz"
            
            # Adding salt at the last of the password
            dataBase_password = password+salt
            # Encoding the password
            hashed = hashlib.md5(dataBase_password.encode()).hexdigest()
            
            data = {
                'email': email,
                'username': username,
                'password': hashed,
                'phone': phone,
            }
            result=create_user(data)
            expiration = datetime.datetime.utcnow() + datetime.timedelta(minutes=50)
            encoded_jwt = jwt.encode(data| {"exp": expiration}, "secret", algorithm="HS256")
            
            return JsonResponse({"result": result, "token": encoded_jwt})
    else:
        return JsonResponse({"error": "Only POST requests are allowed"})

@csrf_exempt
def login(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        email = data.get('email') 
        password = data.get('password')
                
        # adding 5gz as password
        salt = "5gz"
        
        # Adding salt at the last of the password
        dataBase_password = password+salt
        # Encoding the password
        hashed = hashlib.md5(dataBase_password.encode()).hexdigest()
        
        data = {
            'email': email,
            'password': hashed
        }
        result=fetch_user(data)
        if result:
            expiration = datetime.datetime.utcnow() + datetime.timedelta(minutes=50)
            encoded_jwt = jwt.encode(data| {"exp": expiration}, "secret", algorithm="HS256")
            
            return JsonResponse({"result": result, "token": encoded_jwt})
        else:
            return JsonResponse({"error": 'Wrong email or password'}, status=400)
        
    else:
        return JsonResponse({"error": "Only POST requests are allowed"})