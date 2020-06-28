# Deep Racer Model Uploader Web App

## Pre-requisites

* Route53 Domain

## Deploy the main stack

The container image is already pre-built and deployed to a publiv docker hob repository. If you wish to build your own you will need to update the `template.yaml` file with the image location.

### Build the SAM application

>At the time of writing SAM needed the build to be performed inside a container due to a problem with the x-ray module dependencies.

```bash
sam build -u
```

After the build is complete package the stack.

```bash
sam package --output-template-file ./deployment/webapp.yaml --s3-bucket aws-sam-cli-managed-default-samclisourcebucket-fjqlxzpq2ix6 --s3-prefix deepracer-event-webapp
```

After packaging finally deploy the stack.

```bash
sam deploy -t ./deployment/webapp.yaml --stack-name deepracer-event-webapp --s3-bucket aws-sam-cli-managed-default-samclisourcebucket-fjqlxzpq2ix6 --s3-prefix deepracer-event-webapp --capabilities CAPABILITY_IAM --parameter-overrides ParameterKey=Vpc,ParameterValue=vpc-0e3846a3a52a7b0a3 ParameterKey=PublicSubnets,ParameterValue=subnet-0a705eb87f36fd51b,subnet-046c1a529a0006a89,subnet-097aaaf6813bd02d6 ParameterKey=PrivateSubnets,ParameterValue=subnet-0b27c0f4fbe0b839e,subnet-04e7cdefb6498b1c4,subnet-0aedda845fbf4efb5 ParameterKey=HostedZoneName,ParameterValue=deepracer.djohns.com ParameterKey=HostedZoneId,ParameterValue=Z08739983KW4AQ4PPMPG8 --region eu-west-1
```

## Configure the application

Two final steps are required in order to use/test the app.

1) Add user(s) to Cognito
