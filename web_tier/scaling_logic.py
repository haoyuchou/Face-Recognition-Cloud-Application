import boto3
#import threading
import time
import json
import os
from dotenv import load_dotenv

load_dotenv()

AWS_KEY_ID = os.getenv('AWS_KEY_ID')
AWS_ACCESS_KEY= os.getenv('AWS_ACCESS_KEY')
#s3 = boto3.client('s3', region_name='us-east-1', aws_access_key_id=AWS_KEY_ID, aws_secret_access_key=AWS_ACCESS_KEY)
sqs = boto3.client('sqs', region_name='us-east-1', aws_access_key_id=AWS_KEY_ID, aws_secret_access_key=AWS_ACCESS_KEY)
ec2 = boto3.client('ec2', region_name='us-east-1', aws_access_key_id=AWS_KEY_ID, aws_secret_access_key=AWS_ACCESS_KEY)
request_queue_url = "https://sqs.us-east-1.amazonaws.com/851725278093/1227918122-req-queue"
#response_queue_url = "https://sqs.us-east-1.amazonaws.com/851725278093/1227918122-resp-queue"
#ami_id="ami-09be4ca6e1a2b71d9"
#lllll
ami_id="ami-03dbe53b3eba1967b"


def count_app_instances():
    # Use the describe_instances method to retrieve information about EC2 instances
    response = ec2.describe_instances(Filters=[
        {
            'Name': 'tag:Name',
            'Values': ['app-tier*']
        }
    ]
    )

    # Initialize a count variable to track the number of instances
    count = 0

    # Loop through the reservations in the response
    # Iterate through the reservations and instances
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            # Check if the instance state is either running or pending
            if instance['State']['Name'] in ['running', 'pending']:
                count += 1

    return count

def background_task():
    while True:
        # Your while loop logic goes here
        response = sqs.get_queue_attributes(
        QueueUrl=request_queue_url,
        AttributeNames=['ApproximateNumberOfMessages']
    )   
        num_messages = int(response['Attributes']['ApproximateNumberOfMessages'])
        print("Background task is running...")
        print("number of message in the request queue: ", num_messages)
        instance_count = count_app_instances()
        print("instance count: ", instance_count)
        
        if num_messages > 0 and instance_count < 20 and instance_count < num_messages:
            # I need to create num_messages - instance_count number of new instance
            # create one instance
            for i in range(instance_count, num_messages):
                print("create new instance! ", i)
                response = ec2.run_instances(
                ImageId=ami_id,
                InstanceType='t2.micro',
                KeyName='my_key_pair',
                #SecurityGroupIds=security_group_ids,
                MinCount=1,
                MaxCount=1,
                TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': 'app-tier-instance-' + str(i + 1)
                        },
                    ]
                },
            ]
                )

        time.sleep(2)
if __name__ == '__main__':
    background_task()