from flask import Flask, request, Response, stream_with_context
import boto3
import threading
import time
import json
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

AWS_KEY_ID = os.getenv('AWS_KEY_ID')
AWS_ACCESS_KEY= os.getenv('AWS_ACCESS_KEY')
s3 = boto3.client('s3', region_name='us-east-1', aws_access_key_id=AWS_KEY_ID, aws_secret_access_key=AWS_ACCESS_KEY)
sqs = boto3.client('sqs', region_name='us-east-1', aws_access_key_id=AWS_KEY_ID, aws_secret_access_key=AWS_ACCESS_KEY)
ec2 = boto3.client('ec2', region_name='us-east-1', aws_access_key_id=AWS_KEY_ID, aws_secret_access_key=AWS_ACCESS_KEY)
request_queue_url = "https://sqs.us-east-1.amazonaws.com/851725278093/1227918122-req-queue"
response_queue_url = "https://sqs.us-east-1.amazonaws.com/851725278093/1227918122-resp-queue"
ami_id="ami-09be4ca6e1a2b71d9"
#response_dict = {}
# maintain a dict to store value from response queue?

def upload_image_to_s3(file_name, image_file):
    bucket_name = "1227918122-in-bucket"
    object_key = file_name
    s3.upload_fileobj(image_file, bucket_name, object_key)
    # Return the S3 object path
    # "https://1227918122-in-bucket.s3.amazonaws.com/" + file_name
    return "s3://" + bucket_name + "/" + object_key

def upload_to_request_sqs(file_name, s3_path):
    # Send the input file name and S3 object path to the request SQS queue
    message = {
        "input_file_name": file_name,
        "s3_path": s3_path
    }
    response = sqs.send_message(
        QueueUrl=request_queue_url,
        MessageBody=json.dumps(message)
    )

def upload_to_output_s3(key, value):
    bucket_name = '1227918122-out-bucket'
    s3.put_object(Bucket=bucket_name, Key=key, Body=value)

def receive_response_from_sqs():
    # Receive the response from the response SQS queue
    response = sqs.receive_message(
        QueueUrl=response_queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=20
    )
    if 'Messages' in response:
        message = response['Messages'][0]
        sqs.delete_message(QueueUrl=response_queue_url, ReceiptHandle=message['ReceiptHandle'])
        print('delete message !')
        # Upload to output S3 bucket
        message_body = json.loads(message['Body'])
        # Access the "file_name" and "result" keys from the parsed JSON
        file_name = message_body.get("file_name", "").strip('.jpg')
        result = message_body.get("result", "")
        # Upload to output S3 bucket
        upload_to_output_s3(file_name, result)
        return
    else:
        return "Nothing in the response queue"

def filename_in_s3_output(filename):
    output_bucket_name = "1227918122-out-bucket"
    try:
        # Get the object from S3
        response = s3.get_object(Bucket=output_bucket_name, Key=filename.strip('.jpg'))
        # Read the contents of the object
        value = response['Body'].read().decode('utf-8')
        return value
    except s3.exceptions.NoSuchKey:
        # If the key does not exist, return None
        return None



@app.route('/')
def flaskProject():
    return 'Cabo hola viva mexico hellyeah ohhhhh!'

@app.route('/', methods = ['POST'])
def process_image():
    # Increase the timeout for handling requests
    #request.environ['werkzeug.server.shutdown'] = True
    #request.timeout = 300  # Set timeout to 300 seconds (5 minutes)
    if 'inputFile' not in request.files:
        return 'No file part in the request', 400
    
    file = request.files['inputFile']

    if file.filename == '':
        return 'No selected file', 400
    
    if file and file.filename.endswith('.jpg'):
        # Save the file to a desired location
        #file.save('/path/to/save/' + file.filename)
        # upload image to s3
        s3_url = upload_image_to_s3(file.filename, file)
        # upload file name and url to sqs
        upload_to_request_sqs(file.filename, s3_url)
        ans = ""
        # Asynchronously process the response from the response queue
        while True:
            receive_response_from_sqs()
            # if se have my file name
            predict_result = filename_in_s3_output(file.filename)
            if predict_result:
                ans = file.filename + ":" + predict_result
                #yield file.filename + ":" + message_body["result"]
                break
            else:
                time.sleep(2)
        # test_000.jpg:Paul
        '''
        {
    "file_name": "test_000.jpg",
    "result": "Paul"
}
        '''
        #return file.filename + ":" + message_body["result"]
        return ans
    else:
        return 'Invalid file format. Only JPEG files are allowed', 400
    return 'hola'

if __name__ == "__main__":
    # Start the background task in a separate thread
    #background_thread = threading.Thread(target=background_task)
    #background_thread.daemon = True  # Set the thread as daemon so it will be terminated when the main thread exits
    #background_thread.start()
    # start flask
    #app.debug = True
    #app.request_timeout=300
    app.run(threaded=True)