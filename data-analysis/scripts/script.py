import os
import json
import sqlite3
from haralyzer import HarParser
import pandas as pd
import tldextract  # Make sure to install this package
from urllib.parse import urlparse, urlsplit

# Define the directory containing your HAR files
har_directory = '/Users/anastasia/Library/Mobile Documents/com~apple~CloudDocs/UNI/Seminar/DATASET/shops_device2'  # Update this path

# Function to serialize headers into a JSON string
def serialize_headers(headers):
    return json.dumps({header['name']: header['value'] for header in headers})

# Function to infer resource type from URL or MIME type
def infer_resource_type(url, response_headers):
    # Infer from file extension
    path = urlsplit(url).path
    if path:
        extension = os.path.splitext(path)[1].lower()
        if extension in ['.js', '.mjs']:
            return 'script'
        elif extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            return 'image'
        elif extension in ['.css']:
            return 'stylesheet'
        elif extension in ['.html', '.htm']:
            return 'document'
        # Add more conditions as needed based on your requirements

    # Infer from MIME type if extension-based inference was inconclusive
    content_type = next((h['value'] for h in response_headers if h['name'].lower() == 'content-type'), '')
    if 'javascript' in content_type:
        return 'script'
    elif 'image' in content_type:
        return 'image'
    elif 'css' in content_type:
        return 'stylesheet'
    elif 'html' in content_type:
        return 'document'
    # Add more conditions as needed based on your requirements

    return 'other'  # Default to 'other' if no specific type was inferred

# List to hold all the extracted data
data = []

# Iterate through each HAR file in the directory
for filename in os.listdir(har_directory):
    if filename.endswith('.har'):  # Check if the file is a HAR file
        filepath = os.path.join(har_directory, filename)
        directory_name = os.path.basename(os.path.dirname(filepath))  # Get directory name

        try:
            with open(filepath, 'r') as f:
                har_content = json.loads(f.read())
            har_parser = HarParser(har_content)

            base_domain = extract_base_domain(har_parser.pages[0].entries[0]['request']['url'])

            for page in har_parser.pages:
                for entry in page.entries:
                    url = entry['request']['url']
                    domain = tldextract.extract(url).registered_domain
                    is_third_party = base_domain != domain  # Determine third-party request
                    
                    status_code = entry['response']['status']
                    method = entry['request']['method']
                    resource_type = infer_resource_type(url, entry['response']['headers'])
                    request_headers = serialize_headers(entry['request']['headers'])
                    response_headers = serialize_headers(entry['response']['headers'])
                    query_string = json.dumps({item['name']: item['value'] for item in entry['request']['queryString']})

                    data.append([
                        directory_name, filename, url, domain, is_third_party, method, status_code, resource_type,
                        request_headers, response_headers, query_string
                    ])

        except json.decoder.JSONDecodeError as err:
            print(f"Failed to parse {filename}: {err}")

# Convert the data list to a DataFrame
columns = [
    'DirectoryName', 'File', 'URL', 'Domain', 'IsThirdParty', 'Method', 'StatusCode', 'ResourceType',
    'RequestHeaders', 'ResponseHeaders', 'QueryString'
]
df = pd.DataFrame(data, columns=columns)

# Serialize dictionary columns to JSON strings before database insertion
for col in ['RequestHeaders', 'ResponseHeaders', 'QueryString']:
    df[col] = df[col].apply(json.dumps)

# Connect to SQLite database (will create if doesn't exist)
conn = sqlite3.connect('har_data.db')

# Convert DataFrame to SQL table
df.to_sql('tracking_data', conn, if_exists='replace', index=False)

# Close the connection
conn.close()

print("Data extraction and database creation complete!")
