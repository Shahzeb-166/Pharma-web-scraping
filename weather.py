# weather.py
import openmeteo_requests
import requests_cache
from retry_requests import retry
import pandas as pd


def fetch_weather(
    latitude=24.8608,
    longitude=67.0104,
    timezone="Asia/Karachi",
    forecast_days=7
):
    """
    Fetch current + weekly weather data using Open‑Meteo
    """
    cache_session = requests_cache.CachedSession(
        ".weather_cache", expire_after=3600
    )
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)

    openmeteo = openmeteo_requests.Client(session=retry_session)

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_probability_max"
        ],
        "current": [
            "temperature_2m",
            "apparent_temperature"
        ],
        "forecast_days": forecast_days,
    }

    response = openmeteo.weather_api(url, params=params)[0]

    # -------- Current --------
    current = response.Current()
    current_data = {
        "temp": current.Variables(0).Value(),
        "apparent": current.Variables(1).Value(),
    }

    # -------- Daily --------
    daily = response.Daily()
    daily_data = {
        "date": pd.date_range(
            start=pd.to_datetime(daily.Time(), unit="s"),
            periods=daily.Variables(0).ValuesAsNumpy().shape[0],
            freq="D"
        ),
        "max": daily.Variables(0).ValuesAsNumpy(),
        "min": daily.Variables(1).ValuesAsNumpy(),
        "precip": daily.Variables(2).ValuesAsNumpy(),
    }

    daily_df = pd.DataFrame(daily_data)

    return {
        "current": current_data,
        "daily": daily_df
    }

def render_today_weather_widget(current, daily_df):
    today = daily_df.iloc[0]

    return f"""
    <div class="weather-widget">
      <div class="temp">
        {current['temp']:.1f}°C
        <span class="range">
          {today['min']:.0f}° / {today['max']:.0f}°
        </span>
      </div>
      <div class="meta">
        Feels like {current['apparent']:.0f}°C<br>
        Precipitation risk: {today['precip']:.0f}%
      </div>
    </div>
    """


def render_week_weather_cards(daily_df):

    cards = ""

    for _, r in daily_df.iterrows():
        cards += f"""
        <div class="weather-day-card">
          <div class="day">{r['date'].strftime('%a')}</div>
          <div class="temp">
            <span class="max">{r['max']:.0f}°</span>
            <span class="min">{r['min']:.0f}°</span>
          </div>
          <div class="precip">
            💧 {r['precip']:.0f}%
          </div>
        </div>
        """

    return f"""
    <div class="weather-week-cards">
      {cards}
    </div>"""

