import requests

def test_get_flight_data():
    url = "http://localhost:8000/add-flight-api"
    payload = {
        "user_id": "test_user",
        "date": "2025-02-18",
        "flight_number": "BA116",
        "departure_time": "20:00",
        "timezone": "America/New_York"
    }
    response = requests.post(url, json=payload)
    data = response.json()
    print(data)

def test_get_user_flights():
    url = "http://localhost:8000/flights"
    payload = {
        "user_id": "test_user"
    }
    response = requests.get(url, json=payload)
    data = response.json()
    print(data)

def test_manual_insert_flight():
    url = "http://localhost:8000/add-flight-manual"
    payload = {
        "user_id": "test_user",
        "flight_number": "LX188",
        "date": "2025-02-11",
        "airline_name": "Swiss International Air Lines",
        "origin_name": "Zurich Airport",
        "destination_name": "Shanghai Pudong Airport",
    }

    response = requests.post(url, json=payload)
    data = response.json()
    print(data)

def test_delete_user():
    url = "http://localhost:8000/delete-user"
    payload = {
        "user_id": "a349e1c9-a552-4ed9-b7f4-d3a13373a643"
    }
    response = requests.delete(url, json=payload)
    data = response.json()

def test_add_user():
    url = "http://localhost:8000/new-user"
    payload = {
        "name": "test",
        "surname": "user",
        "email": "test@test.com",
        "password": "test"
    }
    response = requests.post(url, json=payload)
    data = response.json()
    print(data)

def test_delete_flight():
    url = "http://localhost:8000/delete-flight"
    payload = {
        "flight_id": "95d46c67-1f84-45b2-bc7f-8eca80e4b7ec"
    }
    response = requests.delete(url, json=payload)
    data = response.json()
    print(data)

if __name__ == "__main__":
    # test_get_flight_data()
    # test_get_user_flights()
    # test_manual_insert_flight()
    # test_delete_user()
    test_delete_flight()