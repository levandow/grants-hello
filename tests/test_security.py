from app.security import verify_password, get_password_hash

def test_password_hashing():
    password = "test_password"
    hashed_password = get_password_hash(password)
    assert verify_password(password, hashed_password)
    assert not verify_password("wrong_password", hashed_password)
