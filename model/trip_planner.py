import pandas as pd
import random
from sklearn.neighbors import NearestNeighbors

# Load cleaned trip data
def load_cleaned_data():
    data = pd.read_csv("data/cleaned_trip_data.csv")
    data["Ratings"] = pd.to_numeric(data["Ratings"], errors="coerce")
    data["Distance(Km)"] = pd.to_numeric(data["Distance(Km)"], errors="coerce")
    data["Time Duration"] = pd.to_numeric(data["Time Duration"], errors="coerce")
    data = data.dropna(subset=["Ratings", "Distance(Km)", "Time Duration"])
    return data

# Get distinct cities for dropdown
def get_distinct_cities(data):
    return sorted(data["City"].dropna().unique())

# ML-based place recommendation using Nearest Neighbors
def recommend_places_ml(city, rating, max_distance, visited_places, df):
    city_data = df[df["City"].str.lower() == city.lower()]
    if city_data.empty:
        return []

    filtered_data = city_data[
        (city_data["Ratings"] >= rating) &
        (city_data["Distance(Km)"] <= max_distance) &
        (~city_data["Place"].isin(visited_places))
    ]
    if filtered_data.empty:
        return []

    features = filtered_data[["Ratings", "Distance(Km)"]].values
    nbrs = NearestNeighbors(n_neighbors=min(5, len(features))).fit(features)
    random_idx = random.randint(0, len(features) - 1)
    distances, indices = nbrs.kneighbors([features[random_idx]])

    return filtered_data.iloc[indices[0]].reset_index(drop=True)

# Convert time in 24-hour format to 12-hour format with AM/PM
def convert_to_12hr_format(time_in_24hr):
    hour = int(time_in_24hr)
    minutes = int((time_in_24hr - hour) * 60)

    if time_in_24hr >= 12:
        period = 'PM'
        if hour > 12:
            hour -= 12
    else:
        period = 'AM'
        if hour == 0:
            hour = 12

    return f"{hour}:{minutes:02d} {period}"

# Generate daily itinerary
def generate_daily_itinerary(city, rating, max_distance, visited_places, df):
    daily_itinerary = []
    current_time = 10.0
    total_time_spent = 0.0
    max_time = 10.0
    lunch_added = False

    # Add breakfast
    breakfast_duration = 1.0
    breakfast_start_time = convert_to_12hr_format(current_time)
    breakfast_end_time = convert_to_12hr_format(current_time + breakfast_duration)
    daily_itinerary.append({
        "time": f"{breakfast_start_time} - {breakfast_end_time}",
        "event": "Breakfast",
        "place": "Enjoy your breakfast",
        "image": ""
    })
    current_time += breakfast_duration

    # Recommend places
    recommended_places = recommend_places_ml(city, rating, max_distance, visited_places, df)

    for i, row in recommended_places.iterrows():
        visit_time = row["Time Duration"]
        if total_time_spent + visit_time > max_time:
            break

        visit_start_time = convert_to_12hr_format(current_time)
        visit_end_time = convert_to_12hr_format(current_time + visit_time)
        daily_itinerary.append({
            "time": f"{visit_start_time} - {visit_end_time}",
            "event": "Visit",
            "place": row["Place"],
            "image": row["Images"]
        })
        visited_places.append(row["Place"])
        current_time += visit_time
        total_time_spent += visit_time

        # Add lunch if it's after 2 PM
        if not lunch_added and current_time >= 14.0:
            lunch_duration = 1.0
            lunch_start_time = convert_to_12hr_format(current_time)
            lunch_end_time = convert_to_12hr_format(current_time + lunch_duration)
            daily_itinerary.append({
                "time": f"{lunch_start_time} - {lunch_end_time}",
                "event": "Lunch",
                "place": "Enjoy your lunch",
                "image": ""
            })
            current_time += lunch_duration
            lunch_added = True

    # Add dinner
    dinner_duration = 1.0
    dinner_start_time = convert_to_12hr_format(max(20, current_time))
    dinner_end_time = convert_to_12hr_format(max(20, current_time) + dinner_duration)
    daily_itinerary.append({
        "time": f"{dinner_start_time} - {dinner_end_time}",
        "event": "Dinner",
        "place": "Enjoy your dinner",
        "image": ""
    })

    return daily_itinerary, visited_places

# Plan the full trip
def plan_trip(city, days, rating, max_distance, df):
    full_itinerary = {}
    visited_places = []

    for day in range(1, days + 1):
        daily_itinerary, visited_places = generate_daily_itinerary(city, rating, max_distance, visited_places, df)
        if daily_itinerary:
            full_itinerary[f"Day {day}"] = daily_itinerary

    return full_itinerary
