from Connection.websocket_client import WSClient
from Service.amStart_chain import ws_amStart_chain
from Service.init_chain import ws_init_chain
from Service.loadmodel_chain import LoadModel
from Service.teaching_chain import Teaching

from utils.token_util import load_config,get_token
from utils.logger import logger

def run_main():
    config = load_config()
    token, user_id = get_token()
    ws_url = config["ws_url"]
    ws_client = WSClient(ws_url, user_id, token)
    try:
        ws_client.connect()
        print("WebSocket连接建立...")

        ws_init_chain(ws_client)

        load_model_instance = LoadModel(ws_client=ws_client)
        load_model_instance.ws_loadmodel_chain()

        started = ws_amStart_chain(ws_client)

        if started:
            teaching_instance = Teaching(ws_client)
            teaching_instance.ws_teaching_chain()
        else:
            logger.error("控制器未启动，跳过示教阶段")

    except Exception as e:
        logger.error(f"运行时发生异常: {e}")
        raise e
    finally:
        if ws_client.connected:
            ws_client.close()
            print("WebSocket连接已关闭")


if __name__ == "__main__":

    run_main()