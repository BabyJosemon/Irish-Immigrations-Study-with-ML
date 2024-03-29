import requests
import tensorflow as tf
import numpy as np
import json
import os
import logging
from dotenv import load_dotenv
import tensorflow_text as text
import mysql.connector
import pandas as pd
from flask import Flask
from flask import request, jsonify
from flask import Response

app = Flask(__name__)

load_dotenv()


# mise en place
savedModels={'goemotion': "savedModels/TransformerSentiment"}
MAX_EMOTIONS_LENGTH=4

@app.route("/api/callmodel", methods=['POST'])
def model_runner():
    data = request.json
    if 'jobID' not in data or 'model_id' not in data or 'median_time' not in data:
        return jsonify({'status': 'error', 'message': 'jobID and model_id are required fields'}), 400
    jobID = data.get('jobID')
    modelID = data.get('model_id')
    median_time = data.get('median_time')
    if modelID not in [1, 2, 3, 4, 5, 6]:
        return jsonify({'status': 'error', 'message': 'Valid values for model_id are 1,2,3,4,5,6'}), 400
    
    class_labels = ['Hateful', 'Non-Hateful', 'Neutral']
    #prediction_summary = {label: 0 for label in class_labels}
    topicCorpus = get_topic_text_from_db(jobID)
    if topicCorpus is None or len(topicCorpus)==0:    
        return jsonify({'status': 'error', 'message': 'topicCorpus not found in DB'}), 400
    testCorpus=get_preprocessed_text_from_db(jobID)
    if testCorpus is None or len(testCorpus)==0:    
        return jsonify({'status': 'error', 'message': 'test_corpus not found in DB'}), 400
    prediction_summary = get_predictions_from_deployment(modelID, jobID)
    prediction_summary = get_predictions_from_go_emotions(prediction_summary, testCorpus, jobID, median_time)
    sentiment_dict = {key: value for key, value in prediction_summary.items() if key not in ['emotions']}
    emotions_json = prediction_summary.get('emotions', {})

    try:
       topicsDetected = topic_detection(topicCorpus)
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return jsonify({'status': 'error', 'message':'Topic modelling error' }), 500

    if add_predictions_to_db(sentiment_dict, jobID, modelID) and add_emotions_results_to_db(emotions_json, jobID) and add_topic_results_to_db(topicsDetected,jobID):
        return jsonify({'status': 'success', 'message': 'Model execution completed successfully'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Failed to execute model_runner, Persistence Error'}), 500

def get_preprocessed_text_from_db(jobID):
    connection = mysql.connector.connect(
        user=os.getenv('MYSQL_ROOT_USERNAME'),
        password=os.getenv('MYSQL_ROOT_PASSWORD'),
        host=os.getenv('MYSQL_HOST'),
        database=os.getenv('MYSQL_DB')
    )

    cursor = connection.cursor()
    cursor.execute('SELECT `sentence` FROM `emotions_texts` WHERE `job_id` = %s;', (jobID,))
    results = cursor.fetchall()
    sentences = [row[0] for row in results]
    return sentences

def add_predictions_to_db(prediction_summary, jobID, modelID):
    models=["CNN", "LSTM", "XGBOOST"]
    connection = mysql.connector.connect(
        user=os.getenv('MYSQL_ROOT_USERNAME'),
        password=os.getenv('MYSQL_ROOT_PASSWORD'),
        host=os.getenv('MYSQL_HOST'),
        database=os.getenv('MYSQL_DB')
    )
    try:
        with connection.cursor() as cursor:
            for label, ratio in prediction_summary.items():
                job_output_query = "INSERT INTO job_output (label, ratio, job_id, model) VALUES (%s, %s, %s, %s)"
                cursor.execute(job_output_query, (label, ratio, jobID, models[modelID - 1]))
            connection.commit()
            return True
    except Exception as e:
        print(f"An error occurred while storing data: {str(e)}")
        return False
    finally:
        connection.close()


def get_topic_text_from_db(jobID):
    topicCorpus = []
    try: 
        connection = mysql.connector.connect(
        user=os.getenv('MYSQL_ROOT_USERNAME'),
        password=os.getenv('MYSQL_ROOT_PASSWORD'),
        host=os.getenv('MYSQL_HOST'),
        database=os.getenv('MYSQL_DB')
        )
        with connection.cursor() as cursor:
            cursor.execute('SELECT `sentence` FROM `topics_tokens` WHERE `job_id` = %s;', (jobID,))
            results = cursor.fetchall()
        for row in results:
           tokens_str = row[0]
           topicCorpus.append(tokens_str)
    except Exception as e:
        logging.error(f"Error: {str(e)}")
    return topicCorpus

def generate_json_data(output, jobID, median_time):
    emotions = {
        0: ["anger", "annoyance", "disapproval"],
        1: ["joy", "amusement", "approval", "excitement"],
        2: ["neutral"],
        3: ["sadness", "disappointment", "embarrassment"],
        4: ["surprise", "realization", "confusion", "curiosity"]
    }

    num_classes = len(emotions)
    class_counts = np.zeros(num_classes, dtype=int)
    
    for label in output:
        class_counts[label] += 1
    
    total_samples = len(output)
    result = []
    
    for idx in range(num_classes):
        emotion_labels = ", ".join(emotions[idx])
        count = class_counts[idx]
        percentage = (count / total_samples) * 100
        result.append({emotion_labels: percentage})

    json_data = {
        "job_id": jobID,
        "result": result,
        "median_time":median_time
    }
    return json_data

def add_emotions_results_to_db(json_data, jobID):
    connection = mysql.connector.connect(
        user=os.getenv('MYSQL_ROOT_USERNAME'),
        password=os.getenv('MYSQL_ROOT_PASSWORD'),
        host=os.getenv('MYSQL_HOST'),
        database=os.getenv('MYSQL_DB')
    )
    try:
        with connection.cursor() as cursor:
            json_string = json.dumps(json_data)
            sql = "INSERT INTO goemotion_result_table (job_id, goemotion_result) VALUES (%s, %s)"
            cursor.execute(sql, (jobID, json_string))
            connection.commit()
            return True
    except Exception as e:
        print("An error occurred while storing data:", str(e))
        return False
    finally:
        connection.close()

def add_topic_results_to_db(topicsDetected, jobID):
    try:
        connection = mysql.connector.connect(
        user=os.getenv('MYSQL_ROOT_USERNAME'),
        password=os.getenv('MYSQL_ROOT_PASSWORD'),
        host=os.getenv('MYSQL_HOST'),
        database=os.getenv('MYSQL_DB')
        )
        with connection.cursor() as cursor:
            sql = "INSERT INTO topics_result_table (job_id, topic_info) VALUES (%s, %s)"
            for topic in topicsDetected:
                cursor.execute(sql, (jobID, json.dumps(topic)))
            connection.commit()
            return True
    except Exception as e:
        print("An error occurred while storing topic data result:", str(e))
        return False
    finally:
        connection.close()

def topic_detection(topicCorpus):
    topics_list = []
    model_base_url = 'http://topic_modelling:8005/predictTopic'
    try: 
        request_body={
            "topic_corpus":topicCorpus
        }
        response = requests.post(model_base_url, json=request_body)
        response_data = response.json()
        if response.status_code == 200:
            return response_data
        else:
            raise ValueError(f"Request failed for topic Modelling {response.status_code}")
    except Exception as e:
        logging.error(f"Error: {str(e)}")
    
    return topics_list

def get_predictions_from_deployment(model_id, job_id):
    model_base_url = 'http://model_deployment:8004/predict'
    try:
        request_body={
            "model_id":model_id,
            "job_id": job_id
        }
        response = requests.post(model_base_url, json=request_body)
        response_data = response.json() 
        if response.status_code == 200:
            return response_data
        elif response.status_code == 400:
            error_message = response_data.get('message', 'Unknown error occurred.')
            raise ValueError(f"Bad Request - {error_message}")
        else:
            raise ValueError(f"Request failed with status code {response.status_code}")
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Request error - {str(e)}")
    except Exception as e:
        raise ValueError(f"Unexpected error - {str(e)}")


def get_predictions_from_go_emotions(prediction_summary, testCorpus, jobID, median_time):
    testCorpus = pd.Series(testCorpus)
    emotion_model = tf.keras.models.load_model(savedModels['goemotion'])
    emotion_predictions = emotion_model.predict(testCorpus)
    emotion_predictions = np.argmax(emotion_predictions, axis=1)
    json_result = generate_json_data(emotion_predictions, jobID, median_time)
    prediction_summary['emotions'] = json_result
    return prediction_summary

if __name__ == '__main__':
    app.run(debug = True, host='0.0.0.0', port=8003)