import os
from flask import Flask
from clients.routes import clients_bp

app = Flask(__name__)

# It's good practice to set a secret key for sessions and WTForms
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_default_fallback_key_for_local_dev')


# Register the blueprint
app.register_blueprint(clients_bp)

if __name__ == '__main__':
    app.run(debug=True, port=5001)