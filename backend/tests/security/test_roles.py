from app.core.security import AuthenticatedUser


def test_staff_and_admin_flags():
    customer = AuthenticatedUser("u1", role="customer")
    agent = AuthenticatedUser("u2", role="support_agent")
    admin = AuthenticatedUser("u3", role="admin")
    assert customer.is_staff is False
    assert agent.is_staff is True
    assert admin.is_admin is True
