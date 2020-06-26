# Deep Racer Model Uploader Web App

## Deploy pre-reqs

* ECR Repository
* Intial Codebuild porject (only needed for initial population of ECR)
* CloudFormation Role for use in CodePipeline de3ployed later

<pre>
sam deploy --template-file _no_trigger/prereqs.yaml --stack-name deepracer-event-webapp-prereqs --capabilities CAPABILITY_IAM
</pre>

### Retrieve CodeBuild Project Name

<pre>
aws cloudformation describe-stacks --stack-name deepracer-event-webapp-prereqs --query 'Stacks[0].Outputs[?OutputKey==`CodeBuildProject`].OutputValue' --output text
</pre>

### Perform the initial build

>Replace the highlighted portion below with the name of the `CodeBuild` project retrieved above.
<pre>
aws codebuild start-build --project-name <mark>CodeBuildProject-xxxxxxxxxxxx</mark>
</pre>

>Now go to the CodeBuild console and verify the build completes successfully before performing the next step.

### Update stack to remove one-time use resources

<pre>
aws cloudformation update-stack --stack-name deepracer-event-webapp-prereqs --use-previous-template  --capabilities CAPABILITY_IAM --parameters ParameterKey=CodeCommitName,ParameterValue=""
</pre>

## Deploy the main stack

### Build the SAM application

>At the time of writing SAM needed the build to be performed inside a container due to a problem with the x-ray module dependencies.
<pre>
sam build -u
</pre>
>Replace the highlighted portion below with the name a bucket in your account that you have access to. SAM will uplaod the Lambda pacakges to this location.
<pre>
sam package --s3-bucket <mark>bucket-name</mark> --s3-prefix tmp --output-template-file ./deployment/template.yaml
</pre>
<pre>
sam deploy --template-file ./deployment/template.yaml --stack-name deepracer-event-webapp --capabilities CAPABILITY_IAM --region eu-west-2

## Configure the application

Two final steps are required in order to use/test the app.

1) Enable the API Key using the API Gateway Console
2) Add user(s) to Cognito
