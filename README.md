# Irish-Immigrations-Study-with-ML

## Databases
### Mongodb
`https://www.mongodb.com/languages/python`

### Amazon RDS

## .env setting
`https://dev.to/jakewitcher/using-env-files-for-environment-variables-in-python-applications-55a1`

## enable vitual env for project
`source myenv/bin/activate`

## Running Backend Services Using Docker in VSCode

### Requirements:
1. Install WSL extension in VSCode and then open the project in 
wsl mode(Short cut : CTRL+SHIFT+P)
![img.png](img.png)


2. Verify the docker is using wsl and is enabled in settings
![img_1.png](img_1.png)

### Commands:
Open the terminal for root folder (Irish-Immigrations-Study-with-ML) in VSCode and type the following commands

1. docker-compose build
2. docker-compose up

### Sending Requests:
1. Sample postman Request for Data Service:
![img_2.png](img_2.png)

Url : http://localhost:8001/comments

Sample Request JSON: {
    "url": "https://www.youtube.com/watch?v=bsWZF7g2R-Q",
    "commentcount": 10,
    "jobid": "4b0ceaf1-704c-465e-bb6a-93e7d1bf8aow",
    "modelid": 1
}
2. Preprocessing Service:

![img_3.png](img_3.png)

Url : http://localhost:8002/api/preprocess

Sample Request JSON: {
    "jobID": "4b0ceaf1-704c-465e-bb6a-93e7d1bf8aow", "model_id": 1
}

3. NLP Service:

![img_4.png](img_4.png)

Url: http://localhost:8003/api/callmodel

Sample Request JSON: {
    "jobID": "4b0ceaf1-704c-465e-bb6a-93e7d1bf8aow", "model_id": 1
}

## Running Backend Services Without Docker:

### Note: Changes Done in this section are for local testing and should not be merged with main branch.

Stop all the containers if running because they are all mapped to 
their respective ports in the localhost. Then before running the services locally
please change the container name to localhost in the URLs used in code 
to call the other services.

For example After containerisation Data Service use http://preprocess_service:8002/api/preprocess to 
call Preprocessing Service. So change it to  http://localhost:8002/api/preprocess in YTComment.py .
Perform these changes in urls used for calls in other services as well.