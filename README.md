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

After the build is complete deploy the stack.
> The command below deploys in 'guided' mode for first time deployment if you save the values into the samconfig.toml file as prompted you are able to perform updates with just `sam delpoy`

```bash
sam deploy -g
```

Finally we need to upload the iam_role.yaml file to the S3 bucket and make it public.

Copy the file from `./flask-app/app/downloads/iam_role_template.yaml` to a new file `iam_role.yaml` and open the file in a text editor. Replace the `{{ EventAccountId }}` (including braces) with the account number being used to deploy this solution. Save the changes and upload the file to the root of the S3 bucket created by the CloudFormation stack. The following code updates the bucket public access settings to allow us to upload a file in `public-read` mode. It then uploads the file and reverts the setting back so that no other files can be uploaded with `public-read` setting.

>Make sure to replace `{Model Data Bucket}` in all 3 lines with the S3 bucket created by the deployment.

```bash
aws s3api put-public-access-block --bucket {Model Data Bucket} --public-access-block-configuration BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3 cp ./flask-app/app/downloads/iam_role.yaml s3://{Model Data Bucket}/iam_role.yaml --acl public-read
aws s3api put-public-access-block --bucket {Model Data Bucket} --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=false,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

## Greengrass Deployment

It is assumed for this solution that you already have a Greengrass core deployed and that a Raspberry Pi is being used for the hardware. If you need help deploying Greengrass you can follow instructions [here](https://docs.aws.amazon.com/greengrass/latest/developerguide/setup-filter.rpi.html) You only need to go as far as the end of Module 2. The Greengrass device will bridge the networks of internet access and the Deep Racer car network.

In addition to this standard Greengrass setup there are a few configurations expected in this specific use case:
- Dual network connections
  - Wireless interface (wlan0) configured using DHCP and connection to the internet
  - Wired interface (eth0) to the DeepRacer router and a static IP. [The static IP is required on the DeepRacer network as there is no DNS available on this network].
- A local folder to store the Deep Racer model files. Can be configured but default path is `/dr_models` and set the mode of this folder to 777 to allow the `ggc_user` that Greengrass runs as to read/write to it.

The remaining configuration is best done through the AWS console.

- Add the Lambda function to the Greengrass group (The function name is shown as an output of deploying the stack).
  - Once added, amend the configuration for the Lambda as follows:
-   - Containerization: No container
-   - Lambda Lifecycle: Make this function long-lived and keep it running indefinitely.
-   - Add the following environment variables:
      - QUEUE_URL: {SQS Queue Url from stack deploy output}
      - LOCAL_FOLDER: /dr_models *Change this here if you have chosen to use a different folder*
- Add IAM Role to Greengrass Group (The role name is shown as an output of deploying the stack).
- Set logging on Greengrass Group to CloudWatch Logs for User Lambdas & Greengrass system

Finally deploy the confiugration to the Greengrass Group.

## Configure the application

Two final steps are required in order to use/test the app.

1) Add user(s) to Cognito
2) Perform an update on the CloudFormation stack to ste the value of the DeployS3Trigger parameter to Yes.
