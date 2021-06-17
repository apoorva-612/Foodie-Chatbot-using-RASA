from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from rasa_sdk import Action
from rasa_sdk.events import SlotSet

import json
import pandas as pd
pd.set_option("display.max_colwidth", None)
from threading import Thread
from flask import Flask
from flask_mail import Mail, Message

global config
zomato = pd.read_csv('zomato.csv')
zomato = zomato.drop_duplicates().reset_index(drop=True)


city_dict = ['Ahmedabad', 'Bengaluru', 'Chennai', 'Delhi', 'Hyderabad', 'Kolkata', 'Mumbai', 'Pune', 'Agra', 'Ajmer', 'Aligarh', 'Amravati', 'Amritsar', 'Asansol', 'Aurangabad', 'Bareilly', 'Belgaum', 'Bhavnagar', 'Bhiwandi', 'Bhopal', 'Bhubaneswar', 'Bikaner', 'Bilaspur', 'Bokaro Steel City', 'Chandigarh', 'Coimbatore', 'Cuttack', 'Dehradun', 'Dhanbad', 'Bhilai', 'Durgapur', 'Dindigul', 'Erode', 'Faridabad', 'Firozabad', 'Ghaziabad', 'Gorakhpur', 'Gulbarga', 'Guntur', 'Gwalior', 'Gurgaon', 'Guwahati', 'Hamirpur', 'Hubli-Dharwad', 'Indore', 'Jabalpur', 'Jaipur', 'Jalandhar', 'Jammu', 'Jamnagar', 'Jamshedpur', 'Jhansi', 'Jodhpur', 'Kakinada', 'Kannur',' Kanpur','Kochi' ,'Kolhapur','Kollam','Kozhikode','Kurnool', 'Ludhiana', 'Lucknow', 'Madurai','Malappuram','Mathura','Mangalore','Meerut','Moradabad','Mysore', 'Nagpur' ,'Nanded', 'Nashik','Nellore','Noida','Patna','Pondicherry', 'Purulia', 'Prayagraj', 'Raipur','Rajkot','Rajahmundry','Ranchi','Rourkela', 'Ratlam', 'Salem','Sangli','Siliguri', 'Solapur','Srinagar','Sultanpur','Surat', 'Thanjavur, ''Thiruvananthapuram', 'Thrissur', 'Tiruchirappalli', 'Tirunelveli', 'Tiruvannamalai', 'Ujjain', 'Bijapur', 'Vadodara', 'Varanasi', 'Vasai-Virar City', 'Vijayawada', 'Visakhapatnam', 'Vellore', 'Warangal']
city_dict = [x.lower() for x in city_dict]


def results(loc,cuisine,price):
    TEMP = zomato[(zomato['Cuisines'].apply(lambda x: cuisine.lower() in x.lower())) & (zomato['City'].apply(lambda x: loc.lower() in x.lower()))]
    if price == 'lesser than 300':
            temp2 =  TEMP[TEMP['Average Cost for two']<300]
            return temp2[['Restaurant Name','Address','Average Cost for two','Aggregate rating']].sort_values(by = 'Aggregate rating', ascending = False)

    elif price == 'between 300 to 700':
            temp2 =  TEMP[(TEMP['Average Cost for two'] >= 300) & (TEMP['Average Cost for two'] < 700)]
            return temp2[['Restaurant Name','Address','Average Cost for two','Aggregate rating']].sort_values(by = 'Aggregate rating', ascending = False)

    else:
            temp2 =  TEMP[TEMP['Average Cost for two']>=700]
            return temp2[['Restaurant Name','Address','Average Cost for two','Aggregate rating']].sort_values(by = 'Aggregate rating', ascending = False)

      
def Config():
	gmail_user = 'foodbotupgrad@gmail.com'
	gmail_pwd = '*********'
	gmail_config = (gmail_user, gmail_pwd)
	return gmail_config

gmail_credentials = Config()
app = Flask(__name__)


mail_settings = {
         "MAIL_SERVER": 'smtp.gmail.com',
         "MAIL_PORT": 465,
         "MAIL_USE_TLS": False,
         "MAIL_USE_SSL": True,
         "MAIL_USERNAME": gmail_credentials[0],
         "MAIL_PASSWORD": gmail_credentials[1]
     }

app.config.update(mail_settings)
mail = Mail(app)


def send_async_email(app, recipient, response):
	with app.app_context():
		if '<mailto' in recipient:
			recipient = recipient.split("|",1)[1]
			recipient = recipient.split(">",1)[0]
		print(recipient)
		msg = Message(subject="Restaurant Details", sender=gmail_credentials[0], recipients=[recipient])
		msg.html =u'<h2>Foodie has found few restaurants for you:</h2>'
		restaurant_names =  response['Restaurant Name'].values
		restaurant_location = response['Address'].values
		restaurant_budget = response['Average Cost for two'].values
		restaurant_rating = response['Aggregate rating'].values
		for i in range(len(restaurant_names)):
			name = restaurant_names[i]
			location = restaurant_location[i]
			budget = restaurant_budget[i]
			rating = restaurant_rating[i]
			msg.html += u'<h3>{name} (Rating: {rating})</h3>'.format(name = name, rating = rating)
			msg.html += u'<h4>Address: {locality}</h4>'.format(locality = location)
			msg.html += u'<h4>Average Budget for 2 people: Rs{budget}</h4>'.format(budget = budget)

		mail.send(msg)

def send_email(recipient, response):
    thr = Thread(target=send_async_email, args=[app, recipient,response])
    thr.start()


class ActionSearchRestaurants(Action):
	def name(self):
		return 'action_restaurant'
		
	def run(self, dispatcher, tracker, domain):
		loc = tracker.get_slot('location')
		cuisine = tracker.get_slot('cuisine')
		price = tracker.get_slot('price')
		global restaurants
		restaurants = results(loc, cuisine, price)

		top5 = restaurants.head(5)
		# top 5 results to display
		if len(top5)>0:
                        dispatcher.utter_message("Showing Top 5 Results")
                        response = ""
                        for index, row in top5.iterrows():
                            response = row['Restaurant Name'] + ' in ' + row['Address'] + ' with approximate budget for two people ' + str(row['Average Cost for two']) + ' has been rated ' + str(row['Aggregate rating'])
                            dispatcher.utter_message(str(response))
                            response = ""
		else:
                            response = 'No restaurants found' 
                            dispatcher.utter_message(str(response))


class Check_location(Action):
    def name(self):
        return 'action_check_location'
    def run(self, dispatcher, tracker, domain):
        loc = tracker.get_slot('location')
        if loc.lower() not in city_dict:
            dispatcher.utter_message("Sorry, we don’t operate in this city")
            return [SlotSet('location', None)]

class SendMail(Action):
	def name(self):
		return 'action_email_restaurant_details'
		
	def run(self, dispatcher, tracker, domain):
		recipient = tracker.get_slot('email')

		top10 = restaurants.head(10)
		send_email(recipient, top10)

		dispatcher.utter_message("Have a great day! Mail is sent")
