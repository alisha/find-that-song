import click
from flask import Flask, request, render_template
from flask_cli import FlaskCLI
app = Flask('myapp')
FlaskCLI(app)

@app.route('/', methods=['GET', 'POST'])
def auth_spotify():
  if request.method == 'POST':
    return 'Spotify worked?'
  else:
    return render_template('welcome.html')