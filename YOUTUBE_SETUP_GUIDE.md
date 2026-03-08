# How to get your `client_secrets.json` for YouTube Upload

To enable automatic YouTube uploads, you need to create an OAuth 2.0 credential in the Google Cloud Console.

### 1. Enable YouTube Data API
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g., "My Video Generator").
3. In the sidebar, go to **APIs & Services > Library**.
4. Search for **"YouTube Data API v3"** and click **Enable**.

### 2. Configure OAuth Consent Screen
1. Go to **APIs & Services > OAuth consent screen**.
2. Select **External** and click **Create**.
3. Fill in the required fields (App name, support email, developer email).
4. In the **Scopes** step, add: `.../auth/youtube.upload`.
5. In the **Test users** step, add your email: `gaurav.jadhav99qa@gmail.com`.
6. Finish the setup.

### 3. Create Credentials
1. Go to **APIs & Services > Credentials**.
2. Click **Create Credentials > OAuth client ID**.
3. Select **Desktop app** as the Application type.
4. Give it a name (e.g., "Video Tool Desktop").
5. Click **Create**.
6. A dialog will appear. Click **Download JSON**.

### 4. Setup in Project
1. Rename the downloaded file to exactly `client_secrets.json`.
2. Move this file into the root folder of this project: `/Users/kalyanibadgujar/Text-To-Video-AI-Tool/`.

### 5. Running the Upload
Once the file is there, you can run the following command in your terminal:
```bash
python utility/video/youtube_uploader.py --file "your_video.mp4" --title "Your Title" --description "Your Description" --tags "space,facts,science"
```
*Note: The first time you run it, a browser window will open asking you to log in and authorize the app.*
