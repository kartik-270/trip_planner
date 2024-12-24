import streamlit as st
import pandas as pd
import random
from sklearn.neighbors import NearestNeighbors

# Streamlit app configuration
st.set_page_config(page_title="Personalized Multi-Day Trip Planner", layout="wide")
background_image_url = "https://images.wallpaperscraft.com/image/single/boat_mountains_lake_135258_1024x768.jpg"  # Replace with your image URL
st.markdown(
    f"""
    <style>
    body {{
        background: url("{background_image_url}") no-repeat center center fixed; 
        background-size: cover;
        opacity: 0.9;
    }}
    .stApp {{
        background-color: rgba(255, 255, 255, 0.8);  /* White background with opacity for form */
        border-radius: 10px;
        padding: 20px;
        max-width: 600px;
        margin: auto;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# Load cleaned trip data
@st.cache_data
def load_cleaned_data():
    data = pd.read_csv("data/cleaned_trip_data.csv")

    # Convert necessary columns to numeric types
    data["Ratings"] = pd.to_numeric(data["Ratings"], errors="coerce")
    data["Distance(Km)"] = pd.to_numeric(data["Distance(Km)"], errors="coerce")
    data["Time Duration"] = pd.to_numeric(data["Time Duration"], errors="coerce")

    # Drop rows with invalid data
    data = data.dropna(subset=["Ratings", "Distance(Km)", "Time Duration"])
    return data

# Extract distinct cities for the dropdown
@st.cache_data
def get_distinct_cities(data):
    return sorted(data["City"].dropna().unique())

# Convert time in 24-hour format to 12-hour format with AM/PM
def convert_to_12hr_format(time_in_24hr):
    hour = int(time_in_24hr)
    minutes = int((time_in_24hr - hour) * 60)  # Convert fractional hours to minutes

    if time_in_24hr >= 12:
        period = 'PM'
        if hour > 12:
            hour -= 12
    else:
        period = 'AM'
        if hour == 0:
            hour = 12

    return f"{hour}:{minutes:02d} {period}"

# ML-based place recommendation using Nearest Neighbors
def recommend_places_ml(city, rating, max_distance, visited_places, df):
    city_data = df[df["City"].str.lower() == city.lower()]
    if city_data.empty:
        st.warning(f"No data found for '{city}'.")
        return []

    # Filter places based on minimum rating, maximum distance, and exclude already visited places
    filtered_data = city_data[
        (city_data["Ratings"] >= rating) &
        (city_data["Distance(Km)"] <= max_distance) &
        (~city_data["Place"].isin(visited_places))
    ]

    if filtered_data.empty:
        st.warning("No places found with the selected criteria.")
        return []

    # Prepare data for ML model
    features = filtered_data[["Ratings", "Distance(Km)"]].values
    nbrs = NearestNeighbors(n_neighbors=min(5, len(features))).fit(features)
    random_idx = random.randint(0, len(features) - 1)  # Pick a random starting point
    distances, indices = nbrs.kneighbors([features[random_idx]])

    # Get recommended places
    recommended_places = filtered_data.iloc[indices[0]].reset_index(drop=True)
    return recommended_places

# Generate itinerary for a single day
def generate_daily_itinerary(city, rating, max_distance, visited_places, df):
    daily_itinerary = []
    current_time = 10.0  # Start at 10:00 AM
    total_time_spent = 0.0
    max_time = 10.0  # Fixed maximum time per day
    lunch_added = False  # To track if lunch has been added

    # Add breakfast
    breakfast_duration = 1.0  # 1 hour
    breakfast_start_time = convert_to_12hr_format(current_time)
    breakfast_end_time = convert_to_12hr_format(current_time + breakfast_duration)
    daily_itinerary.append({
        "time": f"{breakfast_start_time} - {breakfast_end_time}",
        "event": "Breakfast",
        "place": "Enjoy your breakfast",
        "image": ""
    })
    current_time += breakfast_duration  # Update time after breakfast

    # Recommend places using ML model
    recommended_places = recommend_places_ml(city, rating, max_distance, visited_places, df)

    for i, row in recommended_places.iterrows():
        visit_time = row["Time Duration"]  # Time to visit the place
        if total_time_spent + visit_time > max_time:
            break  # Stop adding places if the total time exceeds max_time

        # Add place visit
        visit_start_time = convert_to_12hr_format(current_time)
        visit_end_time = convert_to_12hr_format(current_time + visit_time)
        daily_itinerary.append({
            "time": f"{visit_start_time} - {visit_end_time}",
            "event": "Visit",
            "place": row["Place"],
            "image": row["Images"]
        })
        visited_places.append(row["Place"])  # Mark the place as visited
        current_time += visit_time
        total_time_spent += visit_time

        # Add lunch after 2 PM if it hasn't been added yet
        if not lunch_added and current_time >= 14.0:  # 14.0 = 2:00 PM in 24-hour format
            lunch_duration = 1.0  # 1 hour for lunch
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
    dinner_duration = 1.0  # 1 hour for dinner
    dinner_start_time = convert_to_12hr_format(max(20, current_time))  # Start at 8 PM or later
    dinner_end_time = convert_to_12hr_format(max(20, current_time) + dinner_duration)
    daily_itinerary.append({
        "time": f"{dinner_start_time} - {dinner_end_time}",
        "event": "Dinner",
        "place": "Enjoy your dinner",
        "image": ""
    })

    return daily_itinerary, visited_places

# Generate itinerary for multiple days
# Generate itinerary for multiple days
def plan_trip(city, days, rating, max_distance, df):
    full_itinerary = {}
    visited_places = []  # Keep track of places visited across all days

    for day in range(1, days + 1):
        st.markdown(f"<h3 style='text-align: center;'>Day {day}</h3>", unsafe_allow_html=True)
        daily_itinerary, visited_places = generate_daily_itinerary(city, rating, max_distance, visited_places, df)
        if daily_itinerary:
            full_itinerary[f"Day {day}"] = daily_itinerary
            for item in daily_itinerary:
                st.markdown(f"<div style='text-align: center;'><strong>{item['time']}</strong> - {item['event']}: {item['place']}</div>", unsafe_allow_html=True)
                if item["image"]:
                    st.markdown(f"<div style='text-align: center;'><img src='{item['image']}' width='300' ></div>", unsafe_allow_html=True)
                st.markdown("---")
        else:
            st.warning(f"No more unique places to recommend for Day {day}. Adjust your criteria.")
            break

    return full_itinerary


# Load data
df = load_cleaned_data()

# User interface
st.markdown("<h1 style='text-align: center;'>Trip Planner</h1>", unsafe_allow_html=True)
st.markdown("<h2 style='text-align: center;'>Customize your travel experience</h2>", unsafe_allow_html=True)

# Dropdown for distinct cities
cities = get_distinct_cities(df)
city = st.selectbox("Select the city:", cities)

# Other user inputs
days = st.number_input("Enter the number of days:", min_value=1, max_value=10, step=1, value=3)
rating = st.select_slider("Minimum rating (0-5):", options=[i * 0.5 for i in range(11)], value=4.0)
max_distance = st.number_input("Maximum distance from city center (Km):", min_value=0.0, max_value=50.0, step=1.0, value=10.0)

if st.button("Plan Trip"):
    plan_trip(city, days, rating, max_distance, df)
