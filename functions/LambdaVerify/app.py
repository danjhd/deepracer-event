import json
import boto3
import os

def lambda_handler(event, context):
    print(json.dumps(event))
    after_id = [i['revision'] for i in event['CodePipeline.job']['data']['inputArtifacts'] if i['name'] == 'SourceArtifact'][0]
    com = boto3.client('codecommit')
    commit = com.get_commit(
        repositoryName = os.environ['REPOSITORY_NAME'],
        commitId = after_id
    )
    diff = com.get_differences(
        repositoryName = os.environ['REPOSITORY_NAME'],
        beforeCommitSpecifier = commit['commit']['parents'][0],
        afterCommitSpecifier = after_id
    )
    diff_paths = [d['afterBlob']['path'] for d in diff['differences'] if d['changeType'] != 'D']
    triggers = len([t for t in diff_paths if not(t.startswith(f"{os.environ['REPOSITORY_NAME']}/"))])
    cod = boto3.client('codepipeline')
    if triggers > 0:
        print('Putting Job Success.')
        cod.put_job_success_result(
            jobId = event['CodePipeline.job']['id']
        )
    else:
        print('Putting Job Failure.')
        cod.put_job_failure_result(
            jobId = event['CodePipeline.job']['id'],
            failureDetails = {
            'type': 'JobFailed',
            'message': 'Commit differences contained no files requiring action.',
            'externalExecutionId': context.aws_request_id
            }
        )