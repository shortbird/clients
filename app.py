import os
from flask import Flask
from clients.routes import clients_bp

app = Flask(__name__)

# It's good practice to set a secret key for sessions and WTForms
app.config['SECRET_KEY'] = os.urandom(24)

# Register the blueprint
app.register_blueprint(clients_bp)

if __name__ == '__main__':
    app.run(debug=True)