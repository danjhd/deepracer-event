import logging
import sys
import boto3
import json
import os

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

def long_poll_queue():
    while(True):
        sqs = boto3.resource('sqs')
        queue = sqs.Queue(os.environ['QUEUE_URL'])
        receive_messages = queue.receive_messages(
            AttributeNames = ['All'],
            WaitTimeSeconds = 20
        )
        if len(receive_messages) == 0:
            logger.info('No messages found. Checking again...')
        else:
            for message in receive_messages:
                body = json.loads(message.body)
                logger.info(f"Message found: {json.dumps(body)}")
                if 'Records' in body:
                    for record in body['Records']:
                        if 's3' in record:
                            s3 = boto3.resource('s3')
                            bucket = record['s3']['bucket']['name']
                            key = record['s3']['object']['key']
                            local_path = f"{os.environ['LOCAL_FOLDER']}/{key}"
                            if record['eventName'].startswith('ObjectCreated'):
                                logger.info(f'Downloading file to: {local_path}')
                                folder = os.path.dirname(local_path)
                                if not os.path.exists(folder):
                                    os.makedirs(folder)
                                s3.Object(bucket, key).download_file(local_path)
                            elif record['eventName'].startswith('ObjectRemoved'):
                                logger.info(f'Deleting file from: {local_path}')
                                os.remove(local_path) 
                message.delete()

long_poll_queue()

def lambda_handler(event, context):
    return
