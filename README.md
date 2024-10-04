# AWS re:Invent Planner 2024

This webapp helps you plan your schedule in AWS re:Invent 2024

Live version on: **https://reinvent-planner.richardfan.xyz**

## Deploy

This webapp has 2 parts:

### Frontend

The frontend is a static website, the code is inside `frontend/` directory.

You can create an S3 bucket to host the code and use CloudFront to serve it.

Ref: https://aws.amazon.com/premiumsupport/knowledge-center/cloudfront-serve-static-website/#Using_a_website_endpoint_as_the_origin.2C_with_anonymous_.28public.29_access_allowed


### Backend

The backend is an API scrapper hosted on AWS Lambda

The steps to deploy it is:

1. Create an AWS Secrets Manager secret to store your own AWS re:Invent portal login

   This login is for the scrapper to fetch the seat availability information as it is not available from the public session catalog.

   The secret should be in this JSON format:

   ```json
   {
     "USERNAME":"<username>",
     "PASSWORD":"<password>"
   }
   ```

2. Replace the following value in `backend/lambda_function.py` with yours:

   * `BUCKET_NAME` : The S3 Bucket name where you host the frontend

   * `CLOUDFRONT_DISTRIBUTION_ID` : The ID of CloudFront which you serve the frontend

   * `SECRET_NAME` : The Secrets Manager name you have created in step 1

   * `SECRET_REGION` : The AWS region where you created the Secrets Manager in step 1

3. Create an IAM role for the Lambda function (Ref: https://docs.aws.amazon.com/lambda/latest/dg/lambda-intro-execution-role.html#permissions-executionrole-console)

   The IAM role should have the following permission **(Replace the ARN value with yours):**

   * **AWSLambdaBasicExecutionRole**

   * A custom inline policy
     
     ```json
     {
         "Version": "2012-10-17",
         "Statement": [
             {
                 "Sid": "AllowReadSecret",
                 "Effect": "Allow",
                 "Action": [
                     "secretsmanager:GetSecretValue",
                     "s3:PutObject",
                     "s3:GetObject",
                     "s3:ListBucket",
                     "cloudfront:CreateInvalidation"
                 ],
                 "Resource": [
                     "<secret_manager_arn>",
                     "<s3_bucket_arn>/sessions.json",
                     "<s3_bucket_arn>",
                     "<cloudfront_arn>"
                 ]
             }
         ]
     }
     ```

4. Package the Python dependencies on `requirements.txt` into a Lambda Layer

   Ref: https://aws.plainenglish.io/create-your-own-python-layer-on-aws-lambda-environment-2e5160b66f17

5. Create a Lambda function, using:

   * The code in `backend/` directory

   * The IAM role created in step 2

   * The Lambda Layer created in step 3

   Set the **Handler** value as `lambda_function.lambda_handler`

6. Add a CloudWatch Event to trigger the function periodically (E.g. every 30 minutes)

   Ref:
   
   * https://docs.aws.amazon.com/sdk-for-javascript/v3/developer-guide/scheduled-events-invoking-lambda-run.html

   * https://docs.aws.amazon.com/lambda/latest/dg/services-cloudwatchevents-expressions.html