import functools
import hmac
import os

from flask import Flask, jsonify, request

from . import api
from .log import logger

app = Flask(__name__)

global_store = {}

# 可选鉴权：设置环境变量 EASYTRADER_TOKEN 后，所有接口都需要携带
# X-Auth-Token: <token> 或 Authorization: Bearer <token>
AUTH_TOKEN = os.environ.get("EASYTRADER_TOKEN", "")


def _get_request_token():
    token = request.headers.get("X-Auth-Token", "")
    if token:
        return token
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):]
    return ""


@app.before_request
def check_auth():
    if not AUTH_TOKEN:
        return None
    if not hmac.compare_digest(
        _get_request_token().encode("utf-8"), AUTH_TOKEN.encode("utf-8")
    ):
        return jsonify({"error": "unauthorized"}), 401
    return None


def error_handle(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        # pylint: disable=broad-except
        except Exception as e:
            logger.exception("server error")
            message = "{}: {}".format(e.__class__, e)
            return jsonify({"error": message}), 400

    return wrapper


@app.route("/prepare", methods=["POST"])
@error_handle
def post_prepare():
    json_data = request.get_json(force=True)

    user = api.use(json_data.pop("broker"))
    user.prepare(**json_data)

    global_store["user"] = user
    return jsonify({"msg": "login success"}), 201


@app.route("/balance", methods=["GET"])
@error_handle
def get_balance():
    user = global_store["user"]
    balance = user.balance

    return jsonify(balance), 200


@app.route("/position", methods=["GET"])
@error_handle
def get_position():
    user = global_store["user"]
    position = user.position

    return jsonify(position), 200


@app.route("/auto_ipo", methods=["GET"])
@error_handle
def get_auto_ipo():
    user = global_store["user"]
    res = user.auto_ipo()

    return jsonify(res), 200


@app.route("/today_entrusts", methods=["GET"])
@error_handle
def get_today_entrusts():
    user = global_store["user"]
    today_entrusts = user.today_entrusts

    return jsonify(today_entrusts), 200


@app.route("/history_entrusts", methods=["GET"])
@error_handle
def get_history_entrusts():
    user = global_store["user"]
    history_entrusts = user.history_entrusts

    return jsonify(history_entrusts), 200


@app.route("/today_trades", methods=["GET"])
@error_handle
def get_today_trades():
    user = global_store["user"]
    today_trades = user.today_trades

    return jsonify(today_trades), 200


@app.route("/history_trades", methods=["GET"])
@error_handle
def get_history_trades():
    user = global_store["user"]
    history_trades = user.history_trades

    return jsonify(history_trades), 200

@app.route("/cancel_entrusts", methods=["GET"])
@error_handle
def get_cancel_entrusts():
    user = global_store["user"]
    cancel_entrusts = user.cancel_entrusts

    return jsonify(cancel_entrusts), 200


@app.route("/buy", methods=["POST"])
@error_handle
def post_buy():
    json_data = request.get_json(force=True)
    user = global_store["user"]
    res = user.buy(**json_data)

    return jsonify(res), 201


@app.route("/sell", methods=["POST"])
@error_handle
def post_sell():
    json_data = request.get_json(force=True)

    user = global_store["user"]
    res = user.sell(**json_data)

    return jsonify(res), 201


@app.route("/cancel_entrust", methods=["POST"])
@error_handle
def post_cancel_entrust():
    json_data = request.get_json(force=True)

    user = global_store["user"]
    res = user.cancel_entrust(**json_data)

    return jsonify(res), 201


@app.route("/exit", methods=["GET"])
@error_handle
def get_exit():
    user = global_store["user"]
    user.exit()

    return jsonify({"msg": "exit success"}), 200


def run(port=1430, host=None):
    host = host or os.environ.get("EASYTRADER_HOST", "127.0.0.1")
    if not AUTH_TOKEN:
        logger.warning(
            "未设置 EASYTRADER_TOKEN，接口无鉴权；当前监听 %s:%s", host, port
        )
    # pywinauto 操作的是同一个客户端窗口，必须串行处理请求
    app.run(host=host, port=port, threaded=False)
