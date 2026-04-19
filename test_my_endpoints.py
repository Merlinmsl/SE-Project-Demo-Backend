import requests

def test_endpoints():
    try:
        resp = requests.post("http://localhost:8000/api/v1/users/login", data={"username": "test_student", "password": "password"})
        token = resp.json().get("access_token")
        
        # If we can't login, we just make requests without token to see if server is alive
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        
        # Test study-streak
        r1 = requests.get("http://localhost:8000/api/v1/me/study-streak", headers=headers)
        print("study-streak:", r1.status_code, r1.text[:200])

        r2 = requests.get("http://localhost:8000/api/v1/me/badges", headers=headers)
        print("badges:", r2.status_code, r2.text[:200])
        
    except Exception as e:
        print("Backend might be down?", e)

if __name__ == "__main__":
    test_endpoints()
