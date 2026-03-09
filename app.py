import os
from flask import Flask
from src.view import bp

app = Flask(__name__)
app.register_blueprint(bp)


@app.route("/")
def index():
    return "Hello World!"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8877))
    app.run(host="0.0.0.0", port=port)
