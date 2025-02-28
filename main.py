from pyrogram import Client, filters
import requests, os, asyncio, threading
from Extractor import app

api_id = "21705536"
api_hash = "c5bb241f6e3ecf33fe68a444e288de2d"
bot_token = "7734332695:AAH41Un36PQ5PXW15i9RQ5ANGdXCcnnS7kA"

app = Client("classplus_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

api = 'https://api.classplusapp.com/v2'

headers = {
    "Host": "api.classplusapp.com",
    "x-access-token": "",
    "User-Agent": "Mobile-Android",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://web.classplusapp.com",
    "Referer": "https://web.classplusapp.com/",
    "Region": "IN",
}


def get_course_content(course_id, folder_id=0):
    fetched_contents = ""
    params = {'courseId': course_id, 'folderId': folder_id}
    res = requests.get(f'{api}/course/content/get', headers=headers, params=params)
    if res.status_code == 200:
        res_json = res.json()
        contents = res_json.get('data', {}).get('courseContent', [])
        for content in contents:
            if content['contentType'] == 1:
                sub_contents = get_course_content(course_id, content['id'])
                fetched_contents += sub_contents
            elif content['contentType'] == 2:
                name = content.get('name', '')
                url = requests.get(f'{api}/cams/uploader/video/jw-signed-url', headers=headers, params={'contentId': content['contentHashId']}).json()['url']
                fetched_contents += f'{name}:{url}\n'
            else:
                fetched_contents += f"{content.get('name', '')}:{content.get('url', '')}\n"
    return fetched_contents


@app.on_message(filters.command("login"))
async def classplus_login(client, message):
    try:
        input_msg = await message.reply_text("Send your credentials as shown below:\n\nORG CODE:\nMOBILE NUMBER:\n\nOR\n\nACCESS TOKEN:")
        input_response = await client.listen(message.chat.id)
        creds = input_response.text.strip()

        if '\n' in creds:
            org_code, phone_no = [cred.strip() for cred in creds.split('\n')]
            res = requests.get(f'{api}/orgs/{org_code}')
            if res.status_code == 200:
                org_id = res.json()['data']['orgId']
                data = {'countryExt': '91', 'mobile': phone_no, 'orgCode': org_code, 'orgId': org_id, 'viaSms': 1}
                res = requests.post(f'{api}/otp/generate', data=data, headers=headers)
                if res.status_code == 200:
                    otp_msg = await message.reply_text("Send your OTP:")
                    otp_response = await client.listen(message.chat.id)
                    otp = otp_response.text.strip()
                    data = {"otp": otp, "countryExt": "91", "sessionId": res.json()['data']['sessionId'], "orgId": org_id, "mobile": phone_no}
                    res = requests.post(f'{api}/users/verify', data=data, headers=headers)
                    if res.status_code == 200:
                        token = res.json()['data']['token']
                        headers['x-access-token'] = token
                        await message.reply_text(f"Login Successful! Token:\n`{token}`\n\nSend /courses to continue.")
                    else:
                        await message.reply_text("OTP Verification Failed.")
                else:
                    await message.reply_text("Failed to generate OTP.")
            else:
                await message.reply_text("Invalid ORG Code.")
        else:
            token = creds.strip()
            headers['x-access-token'] = token
            res = requests.get(f'{api}/users/details', headers=headers)
            if res.status_code == 200:
                await message.reply_text("Login Successful! Send /courses to continue.")
            else:
                await message.reply_text("Invalid Token. Try Again.")
    except Exception as e:
        await message.reply_text(f"Error: {e}")


@app.on_message(filters.command("courses"))
async def classplus_courses(client, message):
    try:
        user_id = headers.get('x-access-token')
        res = requests.get(f'{api}/profiles/users/data', headers=headers, params={'userId': user_id, 'tabCategoryId': 3})
        if res.status_code == 200:
            courses = res.json()['data']['responseData']['coursesData']
            if courses:
                text = '\n'.join([f"{i+1}. {course['name']}" for i, course in enumerate(courses)])
                num = await message.reply_text(f"Send the index number of the course to download:\n\n{text}")
                num_response = await client.listen(message.chat.id)
                selected_course_index = int(num_response.text.strip()) - 1
                course_id = courses[selected_course_index]['id']
                course_name = courses[selected_course_index]['name']
                msg = await message.reply_text("Extracting course content...")
                course_content = get_course_content(course_id)
                await msg.delete()
                if course_content:
                    with open("Classplus.txt", 'w') as f:
                        f.write(course_content)
                    await message.reply_document("Classplus.txt", caption=f"Batch Name: {course_name}")
                    os.remove("Classplus.txt")
                else:
                    await message.reply_text("No content found in the course.")
            else:
                await message.reply_text("No courses found.")
        else:
            await message.reply_text("Failed to fetch courses.")
    except Exception as e:
        await message.reply_text(f"Error: {e}")

app.run()
