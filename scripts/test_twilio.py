#!/usr/bin/env python3
"""Test Twilio credentials."""

import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

# Twilio credentials from .env
account_sid = os.getenv('TWILIO_ACCOUNT_SID', 'AC746f6b24b3a0f5d6eba29bdbbe2a5a5b')
auth_token = os.getenv('TWILIO_AUTH_TOKEN', 'df4b2e501c1b46c15587e9ffd6b23145')
phone_number = os.getenv('TWILIO_PHONE_NUMBER', '+18556086555')

print('Testing Twilio credentials...')
print(f'Account SID: {account_sid}')
print(f'Phone Number: {phone_number}')
print()

try:
    # Create Twilio client
    client = Client(account_sid, auth_token)
    
    # Fetch account info to verify credentials
    account = client.api.accounts(account_sid).fetch()
    
    print('✅ Twilio credentials are VALID!')
    print(f'Account Status: {account.status}')
    print(f'Account Friendly Name: {account.friendly_name}')
    print(f'Account Type: {account.type}')
    print(f'Date Created: {account.date_created}')
    
    # Check if the phone number is valid
    print()
    print('Checking phone number...')
    incoming_numbers = client.incoming_phone_numbers.list(phone_number=phone_number)
    
    if incoming_numbers:
        number = incoming_numbers[0]
        print(f'✅ Phone number {phone_number} is VALID!')
        print(f'Phone Number SID: {number.sid}')
        sms_capable = number.capabilities.get('sms', False) if number.capabilities else False
        voice_capable = number.capabilities.get('voice', False) if number.capabilities else False
        print(f'SMS Capable: {sms_capable}')
        print(f'Voice Capable: {voice_capable}')
    else:
        print(f'⚠️ Phone number {phone_number} not found in account')
        print('This could mean the number is not yet purchased or is in a different account')
        
except Exception as e:
    print(f'❌ Twilio credentials FAILED!')
    print(f'Error: {e}')
