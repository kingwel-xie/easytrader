# -*- coding: utf-8 -*-

import pywinauto
import pywinauto.clipboard
from pywinauto import findwindows

from easytrader import grid_strategies
from easytrader.log import logger
from . import clienttrader


class HTClientTrader(clienttrader.BaseLoginClientTrader):
    grid_strategy = grid_strategies.Xls

    @property
    def broker_type(self):
        return "ht"

    def login(self, user, password, exe_path, comm_password=None, **kwargs):
        """
        :param user: 用户名
        :param password: 密码
        :param exe_path: 客户端路径, 类似
        :param comm_password:
        :param kwargs:
        :return:
        """
        self._editor_need_type_keys = False

        try:
            self._app = pywinauto.Application().connect(
                path=self._run_exe_path(exe_path), timeout=1
            )
        # pylint: disable=broad-except
        except Exception:
            self._app = pywinauto.Application().start(exe_path)

            # wait login window ready
            while True:
                try:
                    self._app.top_window().Edit1.wait("ready")
                    break
                except RuntimeError:
                    pass
            self._app.top_window().Edit1.set_focus()
            self._app.top_window().Edit1.type_keys(user)
            self._app.top_window().Edit2.type_keys(password)

            self._app.top_window().button0.click()

            self._app = pywinauto.Application().connect(
                path=self._run_exe_path(exe_path), timeout=10
            )
        self._main = self._app.window(title="网上股票交易系统5.0")
        # 不能等待 ready：登录后弹出的“导航/通知”窗口会禁用主窗口，
        # 导致 ready（visible + enabled）永远无法满足
        self._main.wait("exists visible", timeout=100)
        # 新版客户端登录后约 3 秒才弹出“导航”窗口，需要多观察几秒
        self._close_prompt_windows(watch_seconds=6)
        # 弹窗关闭后主窗口应恢复可用
        self._main.wait("ready", timeout=10)

    @property
    def balance(self):
        self._switch_left_menus(self._config.BALANCE_MENU_PATH)

        return self._get_balance_from_statics()

    def _get_balance_from_statics(self):
        result = {}
        for key, control_id in self._config.BALANCE_CONTROL_ID_GROUP.items():
            try:
                result[key] = float(
                    self._main.child_window(
                        control_id=control_id, class_name="Static"
                    ).window_text()
                )
            except findwindows.ElementNotFoundError:
                # 新版华泰客户端会隐藏部分资金字段（如“资金余额”）
                logger.debug(
                    "未找到资金字段 %s (control_id=%s)，已跳过", key, control_id
                )

        # 资金余额 = 可用金额 + 冻结资金，客户端未展示时由两者计算得出
        if "资金余额" not in result and {"可用金额", "冻结资金"} <= result.keys():
            result["资金余额"] = result["可用金额"] + result["冻结资金"]

        return result


