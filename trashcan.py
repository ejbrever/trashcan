from flask import Flask, request, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
limiter = Limiter(
    app,
    key_func=get_remote_address)

@app.route('/webhook', methods=['POST', 'GET'])
@limiter.limit('5/minute')
def webhook():
    if request.method == 'GET':
        return 'GET not supported', 200

    print('opened trash')
    return 'success', 200


if __name__ == '__main__':
    app.run(port = 8888, host='192.168.86.22')
