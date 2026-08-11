# PROCFILE (The Ignition Key for the Cloud!)
# This tiny text file tells hosting platforms (like Render or Heroku) 
# exactly how to launch your website when it goes live on the internet.

# Breakdown of the launch command:
# 
# 🌐 web:       --> Tells the cloud: "This process is a website that will receive web traffic!"
# 🚀 gunicorn   --> The heavy-duty web server engine we want to use to serve our site.
# 📁 app        --> (First 'app') Tells Gunicorn to open the "app.py" file.
# ⚡ app        --> (Second 'app') Tells Gunicorn to run the Flask variable named "app" inside that file!

web: gunicorn app:app