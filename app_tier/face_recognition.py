#!/usr/bin/env python3.8.0
__copyright__   = "Copyright 2024, VISA Lab"
__license__     = "MIT"




import os
import csv
import sys
import torch
from PIL import Image
from facenet_pytorch import MTCNN, InceptionResnetV1
from torchvision import datasets
from torch.utils.data import DataLoader
import boto3
import json
from ec2_metadata import ec2_metadata
import time
import os
from dotenv import load_dotenv

load_dotenv()

AWS_KEY_ID = os.getenv('AWS_KEY_ID')
AWS_ACCESS_KEY= os.getenv('AWS_ACCESS_KEY')

mtcnn = MTCNN(image_size=240, margin=0, min_face_size=20) # initializing mtcnn for face detection
resnet = InceptionResnetV1(pretrained='vggface2').eval() # initializing resnet for face img to embeding conversion
#test_image = sys.argv[1]




# Initialize S3 client
s3 = boto3.client("s3", aws_access_key_id=AWS_KEY_ID,aws_secret_access_key=AWS_ACCESS_KEY, region_name="us-east-1")


sqs = boto3.client("sqs", aws_access_key_id=AWS_KEY_ID,aws_secret_access_key=AWS_ACCESS_KEY, region_name="us-east-1")








def face_match(img_path, data_path): # img_path= location of photo, data_path= location of data.pt
  # getting embedding matrix of the given img
  img = Image.open(img_path)
  #print(img)
  face, prob = mtcnn(img, return_prob=True) # returns cropped face and probability
  emb = resnet(face.unsqueeze(0)).detach() # detech is to make required gradient false




  saved_data = torch.load('data.pt') # loading data.pt file
  embedding_list = saved_data[0] # getting embedding data
  name_list = saved_data[1] # getting list of names
  dist_list = [] # list of matched distances, minimum distance is used to identify the person




  for idx, emb_db in enumerate(embedding_list):
      dist = torch.dist(emb, emb_db).item()
      dist_list.append(dist)




  idx_min = dist_list.index(min(dist_list))
  return (name_list[idx_min], min(dist_list))
def hola(i):
   print(i)


def process_message(message):
   file_name, s3_url = message["input_file_name"], message['s3_path']
   print("hiii: ", file_name, s3_url)
   # Download the image file from S3
   bucket_name, object_key = s3_url.split("s3://")[1].split("/", 1)
   download_path = os.path.join("/tmp", os.path.basename(object_key))
   s3.download_file(bucket_name, object_key, download_path)
   print("download path: ", download_path)
   #hola(download_path)
   # Perform face recognition
   result = face_match(download_path, 'data.pt')
   print("result: ", result[0])
   return {
       'file_name': file_name,
       'result': result[0]  # Return the name of the recognized person
   }




#result = face_match(test_image, 'data.pt')
#print(result[0])








def send_response_to_sqs(response):
  # Send the response to the response SQS queue
  response_queue_url = "https://sqs.us-east-1.amazonaws.com/851725278093/1227918122-resp-queue"
  sqs.send_message(
      QueueUrl=response_queue_url,
      MessageBody=json.dumps(response)
  )
  print("send to response queue")
'''
python3 face_recognition.py ../dataset/face_images_1000/test_000.jpg
'''
ec2 = boto3.client('ec2', aws_access_key_id=AWS_KEY_ID, aws_secret_access_key=AWS_ACCESS_KEY, region_name="us-east-1")
if __name__ == "__main__":
  # Receive message from the request SQS queue
  instance_id = ec2_metadata.instance_id
  request_queue_url = "https://sqs.us-east-1.amazonaws.com/851725278093/1227918122-req-queue"
  count = 0
  print(instance_id)
  while True:
      response = sqs.receive_message(
          QueueUrl=request_queue_url,
          AttributeNames=['All'],
          MaxNumberOfMessages=1,
          WaitTimeSeconds=20
      )
      #print(response)
      if 'Messages' in response:
          message = json.loads(response['Messages'][0]['Body'])
          print("mmmm: ", message)
          processed_result = process_message(message)
          print("Processed result: ", processed_result)
          #upload_to_output_s3(processed_result['file_name'].strip('.jpg'), processed_result['result'])
          send_response_to_sqs(processed_result)




          # Delete the processed message from the request queue
          receipt_handle = response['Messages'][0]['ReceiptHandle']
          print("receipt_handle: ", receipt_handle)
          sqs.delete_message(
              QueueUrl=request_queue_url,
              ReceiptHandle=receipt_handle
          )
          count = 0
          print('count: ', count)
      else:
          print("no response from request queue")
          count += 1
         
      print("countttttt: ", count)
      if count >= 10:
          # delete ec2 instance
          ec2.terminate_instances(InstanceIds=[instance_id])
          break
      time.sleep(2)    
          # Exit the loop after terminating the instance




