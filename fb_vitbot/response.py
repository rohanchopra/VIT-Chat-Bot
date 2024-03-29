import requests
from wit import Wit
import logging
import json
import os
import re
from fb_vitbot.models import Student as stu

logger = logging.getLogger(__name__)

access_token = 'A6LUMWS4GCYONHIVTBVSA767AYSXCQUW'

final_response  = {}

def send(request, response):
	fb_id = request['session_id']
	text = response['text']
	global final_response
	final_response = response
	post_facebook_message(fb_id,text.decode('utf-8'))
	

def first_entity_value(entities, entity):
	"""
	Returns first entity value
	"""
	if entity not in entities:
		return None
	val = entities[entity][0]['value']
	if not val:
		return None
	return val['value'] if isinstance(val, dict) else val

def get_spotlight(request):

	context = request['context']
	fb_id = request['session_id']

	raw_data = os.popen("curl https://vitacademics-rel.herokuapp.com/api/v2/vellore/spotlight").read()
	data = json.loads(raw_data)
	len_acad = len(data['spotlight']['academics'])

	if(len_acad>0):
		text = 'Academics: \n'
		for i in range(0,len_acad):
			text = text+'* ' + data['spotlight']['academics'][i]['text'] +'\n' + 'Link: https://vtop.vit.ac.in/'+data['spotlight']['academics'][i]['url'] + '\n'

		post_facebook_message(fb_id,text)

	len_coe = len(data['spotlight']['coe'])

	if(len_coe>0):
		text = 'COE: \n'
		for i in range(0,len_coe):
			text = text+'* ' + data['spotlight']['coe'][i]['text'] +'\n'

		post_facebook_message(fb_id,text)

	len_res = len(data['spotlight']['research'])
	if(len_res>0):
		text = 'Research: \n'
		for i in range(0,len_res):
			text = text+'* ' + data['spotlight']['research'][i]['text'] +'\n'

		post_facebook_message(fb_id,text)

	if(len_acad == len_coe == len_res == 0):
		post_facebook_message(fb_id,'No announcement in spotlight section')

	#TODO: Add coe and research links (check for missing and incomplete links)


	return context

def get_attendance(request):
	context = request['context']
	entities = request['entities']

	subject = first_entity_value(entities,'subject')

	fb_id = request['session_id']
	student = stu.objects.get(fb_id=fb_id)
	regno = student.regno
	dob = student.dob
	number = student.number
	student.data,valid = vit_academics_api(regno = regno, dob = dob, number = number)
	logger.debug(student.data)
	context['login'] = valid
	#logger.debug(request)
	context['attendance'] = 0
	#TODO: Bug report for academics api, sometimes courses and withdrawn courses not shown ie array size is zero even after successful execution
	#TODO: Fix multiple login db error
	#TODO: Check cause of error code 12
	#TODO: Figure out labs
	if valid == 1 and subject:
		logger.debug(subject)
		len_course = len(student.data['courses'])
		logger.debug("Courses-")
		logger.debug(len_course)
		for i in range(0,len_course):
			logger.debug(subject)
			logger.debug(student.data['courses'][i]['course_title'])
			if re.search(subject, student.data['courses'][i]['course_title'], re.IGNORECASE):
				context['attendance'] = student.data['courses'][i]['attendance']['attendance_percentage']
	elif valid == 1 and not subject:
		for i in range(0,len_course):
			len_course = student.data['courses']
			for i in range(0,len_course):
				context['attendance'] = context['attendance'] + student.data['courses'][i]['attendance']['attendance_percentage']
			context['attendance'] = context['attendance']/len_course
	student.save()
	return context


def get_response(received_message,fb_id):
	response =  client.run_actions(session_id = fb_id, message = received_message)
	#TODO: Send request (session id) as well
	logger.debug(response)
	#return final_response

def vit_academics_api(regno,dob,number):
	raw_data = os.popen("curl --data \"regno="+regno+"&dob="+dob+"&mobile="+number+"\" https://vitacademics-rel.herokuapp.com/api/v2/vellore/login").read()
	data = json.loads(raw_data)
	code = data['status']['code']
	logger.debug(code)

	if code == 0:
		raw_data = os.popen("curl --data \"regno="+regno+"&dob="+dob+"&mobile="+number+"\" https://vitacademics-rel.herokuapp.com/api/v2/vellore/refresh").read()
		data = json.loads(raw_data)
		valid = 1
	elif code == 12:
		data = ''
		valid = 0
	else:
		data = ''
		valid = 2
	logger.debug(valid)
	return data,valid


def get_data(request):
	fb_id = request['session_id']
	context = request['context']

	student = stu.objects.get(fb_id=fb_id)
	regno = student.regno
	dob = student.dob
	number = student.number

	student.data,valid = vit_academics_api(regno = regno, dob = dob, number = number)
	context['login'] = valid
	student.save()
	return context
    
def del_data(request):
	fb_id = request['session_id']
	student = stu.objects.get(fb_id=fb_id)
	student.delete()

def store_data(request):
	fb_id = request['session_id']
	entities = request['entities']
	context = request['context']

	regno = first_entity_value(entities,'regno')
	dob = first_entity_value(entities,'dob')
	number = first_entity_value(entities,'phoneNumber')
	student = stu(regno = regno,dob = dob, number = number, fb_id = fb_id)
	logger.debug(regno+" " +dob+" "+number+" "+fb_id)
	student.data,valid = vit_academics_api(regno = regno, dob = dob, number = number)
	student.save()
	context['login'] = valid
	logger.debug(valid+10)
	return context

actions = {
	'send': send,
	'getAttendance' : get_attendance,
	'getSpotlight' : get_spotlight,
	'storeData' : store_data,
	'deleteData' : del_data,
}

client = Wit(access_token=access_token, actions=actions)

def post_facebook_message(fbid, received_message):           

	post_message_url = 'https://graph.facebook.com/v2.6/me/messages?access_token=EAADljwd55ogBAJSRkD4JJZBklUPD7AKNb7g5FcTbZASrjJDBifAfz6y3OLJcAGQrYEcHhWAgfqduegl7rlL770u3xU21QTvzpVWtDsWajFguush2bDimEdorL4iT3ZC0kDz6G8khBzXbesxsgO7Spqrwm3aLbS26oCXATOPGAZDZD'


	user_details_url = "https://graph.facebook.com/v2.6/%s"%fbid
	user_details_params = {'fields':'first_name,last_name,profile_pic', 'access_token':'EAADljwd55ogBAJSRkD4JJZBklUPD7AKNb7g5FcTbZASrjJDBifAfz6y3OLJcAGQrYEcHhWAgfqduegl7rlL770u3xU21QTvzpVWtDsWajFguush2bDimEdorL4iT3ZC0kDz6G8khBzXbesxsgO7Spqrwm3aLbS26oCXATOPGAZDZD'}

	user_details = requests.get(user_details_url, user_details_params).json()

	response_msg = json.dumps({"recipient":{"id":fbid}, "message":{"text":received_message}})
	status = requests.post(post_message_url, headers={"Content-Type": "application/json"},data=response_msg)
	logger.debug(status.json())

