# core/auth_service.py
class AuthService:
    def __init__(self):
        # 默认高阶管理员凭证
        self._default_user = "admin"
        self._default_pass = "123456"

    def verify(self, username, password):
        """执行安全验证逻辑"""
        if username == self._default_user and password == self._default_pass:
            return True, "认证成功"
        return False, "系统密钥或凭证错误"