import json
import boto3
import re
import os
import logging
from botocore.exceptions import ClientError
from aws_xray_sdk.core import xray_recorder, patch_all

patch_all()

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    print(json.dumps(event))
    try:
        # Assume the role provided to get temporary credentials
        logger.info('Getting temporary credentials...')
        role_arn = event['queryStringParameters']['RoleArn']
        creds = AssumeRole(role_arn, context.function_name)
        src_account = role_arn.split(':')[4]
        # Check which resource was triggered in API Gateway.
        if event['resource'] == '/models':
            logger.info('API call for "get model list" received...')
### List Models ###
            # Set region to us-east-1 if not supplied, since Deep Racer is only available in us-east-1 at present.
            source_region = 'us-east-1' if 'Region' not in event['queryStringParameters'] else event['queryStringParameters']['Region']
            logger.info(f'Sagemaker region set to {source_region}.')
            # Get Deep Racer Models
            models = GetDeepRacerModels(creds, source_region, src_account)
            return {
                'statusCode': 200,
                'body': json.dumps({'models': models})
            }
        elif event['resource'] == '/models/{Region}/{JobId}':
            logger.info('API call for "upload model" received...')
### Upload or Delete Model ###
            source_region = event['pathParameters']['Region']
            logger.info(f'Sagemaker region received as {source_region}.')
            # Create clients to use
            sagemaker, src_s3 = GetClients(creds, source_region)
            # Get training job details
            logger.info(f"Getting Sagemaker training job: {event['pathParameters']['JobId']}...")
            model = GetDeepRacerModelInfo(sagemaker, src_s3, {'TrainingJobName': event['pathParameters']['JobId'], 'Region': source_region}, src_account)
            logger.info(model)
            # Build destination S3 key
            destination_key = f"{model['ModelName']}-{src_account}-{model['Region']}.tar.gz"
            logger.info(f'Destination key determined as {destination_key}.')
            # Check if destination key already exists
            dst_s3 = boto3.resource('s3')
            if S3ObjectExists(dst_s3, os.environ['DESTINATION_BUCKET'], destination_key):
                logger.info(f'Destination key already exists.')
                # Check for GET ot DELETE method
                if event['httpMethod'] == 'GET':
                    # Upload model request
                    return {
                        'statusCode': 200,
                        'body': json.dumps({
                            'message': 'Model already present.'
                        })
                    }
                elif event['httpMethod'] == 'DELETE':
                    # Delete model request
                    dst_obj = dst_s3.Object(os.environ['DESTINATION_BUCKET'], destination_key)
                    dst_obj.delete()
                    return {
                        'statusCode': 200,
                        'body': json.dumps({
                            'message': 'Model deleted.'
                        })
                    }
            else:
                # Check for GET ot DELETE method
                if event['httpMethod'] == 'GET':
                    # Upload model request
                    # Download output model to local tmp folder
                    logger.info(f"Downloading file: {model['S3ModelArtifacts']}...")
                    src_s3.meta.client.download_file(model['S3ModelArtifacts'].split('/', 3)[2], model['S3ModelArtifacts'].split('/', 3)[3], f'/tmp/{destination_key}')
                    logger.info('Download complete.')
                    # Upload to new destination folder
                    logger.info(f"Uploading file: s3://{os.environ['DESTINATION_BUCKET']}/{destination_key}...")
                    dst_s3.meta.client.upload_file(f'/tmp/{destination_key}', os.environ['DESTINATION_BUCKET'], destination_key)
                    logger.info('Upload complete.')
                    # Clean up local tmp
                    logger.info(f'Deleting local file: /tmp/{destination_key}...')
                    os.remove(f'/tmp/{destination_key}')
                    logger.info('Delete complete.')
                    return {
                        'statusCode': 200,
                        'body': json.dumps({
                            'message': 'Model uploaded.'
                        })
                    }
                elif event['httpMethod'] == 'DELETE':
                    # Delete model request
                    return {
                        'statusCode': 200,
                        'body': json.dumps({
                            'message': 'Model was not uploaded so nothing to delete.'
                        })
                    }

    except ClientError as e:
        logger.error(e)
        # Update error message before returning it to API Gateway so that message is customer facing.
        if e.operation_name == 'AssumeRole':
            error_message = re.sub(r'User:\sarn:\S+', 'User', str(e))
        else:
            error_message = re.sub(r'User:\sarn:\S+', f'Role: {role_arn}', str(e))
        return {
            'statusCode': e.response['ResponseMetadata']['HTTPStatusCode'],
            'body': json.dumps({
                'errorMessage': error_message
            })
        }

@xray_recorder.capture('AssumeRole')
def AssumeRole(role_arn, session_name):
    sts = boto3.client('sts')
    logger.info(f'Attempting to assume role: {role_arn}...')
    assume_role = sts.assume_role(
        RoleArn = role_arn,
        RoleSessionName = session_name
    )
    logger.info('Role assumed')
    return assume_role['Credentials']

@xray_recorder.capture('GetDeepRacerModels')
def GetDeepRacerModels(creds, region, src_account):
    # Create clients to use
    sagemaker, src_s3 = GetClients(creds, region)
    models = {}
    for bucket in src_s3.buckets.all():
        # Find the S3 bucket used by DeepRacer
        if bucket.name.startswith('aws-deepracer-'):
            for o in bucket.objects.filter(Prefix='DeepRacer-SageMaker-rlmdl-'):
                # Just keys for model files only
                if o.key.endswith('model.tar.gz'):
                    model = GetDeepRacerModelInfo(sagemaker, src_s3, {'TrainingJobName': o.key.split('/')[1], 'Region': region}, src_account)
                    model_name = model.pop('ModelName')
                    if model_name in models:
                        # Duplicate found. Replace the existing info if the model is newer (training job name contains dt in YYYYMMDDHHMMSS format)
                        if models[model_name]['Region'] == model['Region'] and models[model_name]['TrainingJobName'] > model['TrainingJobName']:
                            models[model_name] = model
                    # No duplicate so just add it to the dict
                    else:
                        models[model_name] = model
    # Convert the dict to an list so that we can sort it
    models = [v.update({'ModelName': k}) or v for k,v in models.items()]
    # Return the sorted list
    return sorted(models, key=lambda k: k['ModelName'])

@xray_recorder.capture('GetClients')
def GetClients(creds, region):
    # Create Sagemaker client to be able to get Deep Racer training jobs
    sagemaker = boto3.client(
        'sagemaker',
        aws_access_key_id = creds['AccessKeyId'],
        aws_secret_access_key = creds['SecretAccessKey'],
        aws_session_token = creds['SessionToken'],
        region_name = region
    )
    # Create S3 client to be able to check if the model output still exists (we only return model names for models where the output exists)
    s3 = boto3.resource(
        's3',
        aws_access_key_id = creds['AccessKeyId'],
        aws_secret_access_key = creds['SecretAccessKey'],
        aws_session_token = creds['SessionToken']
    )
    return sagemaker, s3

@xray_recorder.capture('GetDeepRacerModelInfo')
def GetDeepRacerModelInfo(sagemaker, src_s3, model, src_account):
    # Get training job details
    training_job = sagemaker.describe_training_job(TrainingJobName = model['TrainingJobName'])
    # Split the s3 path for the reward function path hyper parameter to extract the model name
    model['ModelName'] = training_job['HyperParameters']['reward_function_s3_source'].split('/')[4]
    # Set the uploaded property based upon whether a model with the same name already exists in our S3 bucket therefore indicating the model has already been uploaded.
    model['Uploaded'] = S3ObjectExists(boto3.resource('s3'), os.environ['DESTINATION_BUCKET'], f"{model['ModelName']}-{src_account}-{model['Region']}.tar.gz")
    return model

@xray_recorder.capture('S3ObjectExists')
def S3ObjectExists(client, pathORbucket, key=None):
    # Use S3 metadata property to detect is S3 object already exists or not
    if key is None:
        key = pathORbucket.split('/', 3)[3]
        bucket = pathORbucket.split('/', 3)[2]
    else:
        bucket = pathORbucket
    obj = client.Object(bucket, key)
    try:
        obj.metadata
        logger.info(f's3://{bucket}/{key} exists.')
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            logger.info(f's3://{bucket}/{key} does not exist.')
            return False
        else:
            logger.error(e)
            raise e
