import pandas as pd
import re
from email_validator import validate_email, EmailNotValidError

def get_primary_email(email_str):
    # If multiple emails are comma-separated, split and grab the first clean one
    if pd.isna(email_str) or str(email_str).strip().lower() in ['n/a', 'nan']:
        return ""
    
    # Split on commas or spaces and look for the first match
    parts = re.split(r'[,\s]+', str(email_str))
    for part in parts:
        part_clean = part.strip()
        if "@" in part_clean:
            return part_clean
    return ""

def clean_website(url_str):
    # Filter out internal yellowpages redirects to provide a clean corporate domain column
    url_str = str(url_str).strip()
    if pd.isna(url_str) or url_str.lower() in ['n/a', 'nan'] or "yellowpages.com" in url_str:
        return "N/A"
    return url_str

def validate_and_clean_crm():
    print("Reading raw_leads.csv data...")
    try:
        df = pd.read_csv("raw_leads.csv")
    except FileNotFoundError:
        print("Error: Ensure your raw data output file is named 'raw_leads.csv'")
        return

    # STEP 1: Remove perfect duplicates instantly
    print(f"Initial raw rows: {len(df)}")
    df = df.drop_duplicates(subset=["Company Name", "Phone"])
    print(f"Rows remaining after deduplication: {len(df)}")

    # STEP 2: Clean corporate links and isolate single email values
    df["Website"] = df["Website"].apply(clean_website)
    df["Cleaned Email"] = df["Raw Email"].apply(get_primary_email)

    validated_emails = []
    deliverability_status = []

    print("\nRunning email deliverability checks (syntax + domain MX records)...")
    for index, row in df.iterrows():
        email = row["Cleaned Email"]
        
        if not email:
            validated_emails.append("")
            deliverability_status.append("No Email Found")
            continue
            
        try:
            # Validates email format structure and checks live domain MX server records
            valid_info = validate_email(email, check_deliverability=True)
            validated_emails.append(valid_info.normalized)
            deliverability_status.append("Verified Deliverable")
        except EmailNotValidError as e:
            # Catches syntax typos, dead domains, or formatting errors
            validated_emails.append(email)
            deliverability_status.append(f"Invalid Address: {str(e)}")

    # STEP 3: Re-map cleaned structure columns into your data frame
    df["Verified Email"] = validated_emails
    df["Status"] = deliverability_status

    # Drop old raw sorting work column
    df = df.drop(columns=["Raw Email", "Cleaned Email"])

    # STEP 4: Export to Excel/CSV for clean CRM import mapping
    output_filename = "crm_final_import_ready.csv"
    df.to_csv(output_filename, index=False)
    
    print("\n" + "="*50)
    print("SUCCESS! CRM DATA EXTRACTION PIPELINE COMPLETE")
    print(f"Clean leads exported to: {output_filename}")
    print("="*50)

if __name__ == "__main__":
    validate_and_clean_crm()
