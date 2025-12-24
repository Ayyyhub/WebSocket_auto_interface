# Teaching.arl_id 这类副作用管理


# Interface/side_effect.py

from utils.logger import logger

def handle_side_effect(owner, func, resp):
    if not owner or not resp or not resp.get("success"):
        return

    # 示例：生成 arl
    if func == "simArcs.aamGenerateArlProgramFromRecords":
        owner.arl_id = resp["ret"][0]
        logger.info(f"生成 arl_id: {owner.arl_id}")

    elif func == "simArcs.aamCreateTeachingPath":
        owner.collect_point_path_id = resp["ret"][0]
        logger.info(f"生成 collect_point_path_id: {owner.collect_point_path_id}")
