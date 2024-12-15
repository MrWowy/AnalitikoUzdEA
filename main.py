import matplotlib.pyplot as plt
import pandas as pd
import requests
from datetime import datetime, timedelta
import pytz
import time
import seaborn as sns

"""
1) Duomenų nuskaitymas vyksta per atskirą klasę. Į šį objektą nurdoma vietovės kodas, API URL. Ši klasė turi turėti du metodus:
        a) Istorinių duomenų nuskaitymas už nurodytą laiko intervalą nuo - iki;
        b) Prognozės duomenų nuskaitymas;
    Abiem atvejais duomenys turėtų būti gražinami pandas. DataFrame  formatu, kur indeksas yra laikas (pd.DatetimeIndex) su įvertinta laiko zona;

Aš dirbes tik su c# OOP ir python turi savo niuancu apie kuriuos man reiktu pasidomėti. Todėl klase praleisiu ir viska padarysiu ant funkcijų
"""
def get_forecast_data(location_code:str, api_url:str):

    url = f"{api_url}/places/{location_code}/forecasts/long-term"
    response = requests.get(url)
    response.raise_for_status() # Check for HTTP error
    data = response.json()

    # Cast response data as dataframe
    forecast = data["forecastTimestamps"]
    forecast_df = pd.DataFrame(forecast)
    forecast_df["forecastTimeUtc"] = pd.to_datetime(forecast_df["forecastTimeUtc"], utc=True)
    forecast_df.set_index("forecastTimeUtc", inplace=True)

    return forecast_df

def get_historical_data(station_code:str, api_url:str, start_date, end_date):

    all_historical = []
    
    # Collect data by going back in time range
    current_date = end_date
    while current_date >= start_date:
        date_str = current_date.strftime('%Y-%m-%d')
        url = f"{api_url}/stations/{station_code}/observations/{date_str}"
        response = requests.get(url)
        response.raise_for_status() # Check for HTTP error
        data = response.json()

        # Extract observations if available
        observations = data.get("observations", [])
        if observations:
            day_df = pd.DataFrame(observations)
            day_df['observationTimeUtc'] = pd.to_datetime(day_df['observationTimeUtc'], utc=True)
            day_df.set_index('observationTimeUtc', inplace=True)
            all_historical.append(day_df)

        # Enforce rate limit: delay 0.5 seconds per request
        time.sleep(0.5)

        # Get previous day
        current_date -= timedelta(days=1)

    # Combine all collected data into a single DataFrame
    if all_historical:
        final_df = pd.concat(all_historical)
        return final_df

"""
2) Nuskaičius istorinius duomenis už praeitus metus (laikotarpis nuo šiandien iki metai atgal) suskaičiuoti ir atvaizduoti šiuos rodiklius:
        a) Vidutinė metų temperatūra, oro drėgmė;
        b) Vidutinė metų dienos, ir nakties temperatūra priimant kad skaičiuojama LT laiko zonoje ir diena yra tarp 08:00 ir 20:00;
        c) Kiek savaitgalių (šeštadienis/sekmadienis - 1 savaitgalis) per šį laikotarpį buvo prognozuojama kad lis;
"""
def calculate_yearly_metrics(df):
    avg_temp = df['airTemperature'].mean()
    avg_humidity = df['relativeHumidity'].mean()
    
    day_time = df.between_time('08:00', '20:00')
    night_time = df.between_time('20:00', '08:00')
    
    avg_day_temp = day_time['airTemperature'].mean()
    avg_night_temp = night_time['airTemperature'].mean()
    
    weekends = df[df.index.dayofweek >= 5]
    rainy_weekends = weekends[weekends['conditionCode'].str.contains('rain', na=False)]
    num_rainy_weekends = rainy_weekends.index.to_period('W').nunique()
    
    return avg_temp, avg_humidity, avg_day_temp, avg_night_temp, num_rainy_weekends

"""
3) Nuskaičius prognozės duomenis juos apjungti su istoriniais. Atvaizduoti grafiką, kuris rodo paskutinės savaitės išmatuotą temperatūrą ir ateinančio periodo prognozuojama temperatūrą.
"""
def plot_temperature_comparison(historical_df, forecast_df):
    """
    Plot temperature comparison for the last week and forecast period.
    """
    last_week = historical_df.loc[
    historical_df.index >= (historical_df.index.max() - pd.Timedelta(days=7))
]
    forecast_period = forecast_df[['airTemperature']]

    plt.figure(figsize=(12, 6))
    sns.lineplot(data=last_week['airTemperature'], label='Historical (last week)', marker='o')
    sns.lineplot(data=forecast_period['airTemperature'], label='Forecast', marker='o')
    
    plt.title('Temperature Comparison: Last Week vs Forecast')
    plt.ylabel('Temperature (°C)')
    plt.xlabel('Time')
    plt.legend()
    plt.grid()
    plt.show()

"""
4) Visi nuskaityti duomenys yra valandiniai. Parašyti funkciją, į kurią padavus temperatūros pandas. Series suskaičiuotų tarpines reikšmes ir pagražintų rezultatą pandas. Series kurio dažnis yra 5 minutės. Tarpines reikšmes interpoliuoti.
"""
def interpolate_temperature(series):
    """
    Interpolate temperature series to 5-minute frequency.
    """
    series = series.resample('5T').interpolate(method='linear')
    return series


if __name__ == "__main__":
    # Location codes
    location_code = "kaunas"
    station_code = "kauno-ams"
    api_url = "https://api.meteo.lt/v1"

    # Get current date and 1 year ago
    end_date = datetime.now(pytz.timezone('Europe/Vilnius'))
    start_date = end_date - timedelta(days=365)

    # Run functions
    forecast_data = get_forecast_data(location_code, api_url)
    historical_data = get_historical_data(station_code, api_url, start_date, end_date)

    avg_temp, avg_humidity, avg_day_temp, avg_night_temp, rainy_weekends = calculate_yearly_metrics(historical_data)
    print(f"Vidutinė metų temperatūra: {avg_temp:.2f} °C")
    print(f"Vidutinė metų oro drėgmė: {avg_humidity:.2f} %")
    print(f"Vidutinė dienos temperatūra: {avg_day_temp:.2f} °C")
    print(f"Vidutinė nakties temperatūra: {avg_night_temp:.2f} °C")
    print(f"Kiek savaitgalių buvo prognozuojamas lietus: {rainy_weekends}")

    plot_temperature_comparison(historical_data, forecast_data)

    interpolated_series = interpolate_temperature(historical_data['airTemperature'])
    print(interpolated_series.head())