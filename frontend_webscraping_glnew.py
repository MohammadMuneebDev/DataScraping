from playwright.sync_api import sync_playwright
import json
import re

def fetch_page_data(page, page_number):
    """Fetch data from the current page and save it to a JSON file."""
    page.wait_for_selector('table', timeout=10000)

    # Extract table headers
    headers = page.query_selector_all('table th')
    header_list = [header.inner_text().strip() for header in headers]

    # Extract table data
    rows = page.query_selector_all('table tr')
    extracted_data = []

    for row in rows:
        cells = row.query_selector_all('td')
        if cells:
            row_data = {}
            for index, cell in enumerate(cells):
                cell_text = cell.inner_text().strip()
                # Use the header as the key
                if index < len(header_list):
                    row_data[header_list[index]] = {
                        'text': cell_text,
                        'title': cell.get_attribute('title') or ''  # Fetch title attribute if it exists
                    }
            extracted_data.append(row_data)

    # Save the extracted data to a JSON file for the current page
    filename = f'page_data_{page_number}.json'
    with open(filename, 'w', encoding='utf-8') as json_file:
        json.dump(extracted_data, json_file, ensure_ascii=False, indent=2)
        print(f"Data saved to {filename}")

    return header_list  # Return header list for further processing




def fetch_meeting_data(browser, meeting_link, visit_number):
    """Fetch detailed meeting data from the specified link in a new tab and save it to a JSON file."""
    print(f"Visiting meeting link: {meeting_link}")

    # Open a new tab
    new_page = browser.new_page()
    new_page.goto(meeting_link)
    new_page.wait_for_load_state("domcontentloaded")

    # Wait for the table with meeting details to load
    new_page.wait_for_selector('table', timeout=10000)

    # Extract table headers (th)
    headers = new_page.query_selector_all('table th')
    header_list = [header.inner_text().strip() for header in headers]

    # Extract table data (tr)
    rows = new_page.query_selector_all('table tr')
    extracted_meeting_data = []

    for row in rows:
        # Fetch all td elements
        cells = row.query_selector_all('td')
        if cells:  # Ensure there are cells to process
            row_data = {}
            for index, cell in enumerate(cells):
                # Check if the cell is visible
                if cell.is_visible():
                    # Fetch the main text content of the cell
                    cell_text = cell.inner_text().strip()

                    # Only proceed if cell_text is not empty and we have a corresponding header
                    if cell_text and index < len(header_list):
                        header = header_list[index]
                        row_data[header] = {
                            'text': cell_text,
                            'title': cell.get_attribute('title') or ''
                        }

            # Swap the data between "Shares Voted" and "For/Against Management"
            if 'Shares Voted' in row_data and 'For/Against Management' in row_data:
                row_data['Shares Voted']['text'], row_data['For/Against Management']['text'] = (
                    row_data['For/Against Management']['text'],
                    row_data['Shares Voted']['text']
                )

            # Avoid adding incomplete or empty rows
            if row_data and all(key in row_data for key in ['Item', 'Proposal Description', 'Vote Decision']):
                item_text = row_data['Item']['text']
                if item_text not in [entry['Item']['text'] for entry in extracted_meeting_data]:
                    extracted_meeting_data.append(row_data)

    # Save the extracted meeting data to a JSON file
    filename = f'meeting_data_{visit_number}.json'
    with open(filename, 'w', encoding='utf-8') as json_file:
        json.dump(extracted_meeting_data, json_file, ensure_ascii=False, indent=2)
        print(f"Meeting data saved to {filename}")

    # Close the new tab
    new_page.close()





def handle_pagination(page, current_page, total_pages):
    """Handle pagination by clicking the Next button and waiting for the page to load."""
    if current_page < total_pages:  # Avoid clicking next on the last page
        next_button_selector = 'button[title="Next"]'
        try:
            page.wait_for_selector(next_button_selector, timeout=10000)
            next_button = page.query_selector(next_button_selector)
            if next_button and not next_button.is_disabled() and next_button.is_visible():
                next_button.click()
                print("Navigated to the next page.")
                
                # Wait for the page to load
                page.wait_for_load_state("domcontentloaded")  # Wait for the page to load completely
                
                # Ensure the table is visible after navigation
                page.wait_for_selector('table', timeout=10000)

                # Optionally wait a moment for data to settle
                page.wait_for_timeout(2000)  # Adjust this timeout as needed

            else:
                print("Next button is disabled, not visible, or not found.")
        except Exception as e:
            print(f"Error clicking the next button: {e}")




def scrape_votedisclosure(start_date, end_date):
    """Main function to scrape data from the Vote Disclosure website."""
    visited_links = set()  # Cache to keep track of visited links
    visit_number = 1  # For naming meeting files

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Navigate to the target page
        page.goto("https://votedisclosure.glasslewis.com/Russell%20Australia", timeout=100000)
        page.wait_for_load_state("domcontentloaded")
        print("Page loaded successfully.")

        # Wait for the form to be present and visible
        page.wait_for_selector('form[novalidate]', timeout=10000)

        # Input selectors for date inputs
        start_date_input_selector = 'tui-input-date[formcontrolname="start"] input[automation-id="tui-primitive-textfield__native-input"]'
        end_date_input_selector = 'tui-input-date[formcontrolname="end"] input[automation-id="tui-primitive-textfield__native-input"]'

        # Fill in start and end dates
        page.wait_for_selector(start_date_input_selector, timeout=5000)
        start_input_element = page.query_selector(start_date_input_selector)
        start_input_element.fill(start_date)

        page.wait_for_timeout(1000)

        page.wait_for_selector(end_date_input_selector, timeout=5000)
        end_input_element = page.query_selector(end_date_input_selector)
        end_input_element.fill(end_date)

        # Wait a moment after filling the dates
        page.wait_for_timeout(1000)

        # Click all checkboxes
        checkboxes = page.query_selector_all('input[automation-id="tui-checkbox__native"]')
        for checkbox in checkboxes:
            checkbox.check()

        # Click the Apply button
        apply_button_selector = 'button[data-testid="main-page-submit-button"]'
        page.wait_for_selector(apply_button_selector, timeout=5000)
        apply_button = page.query_selector(apply_button_selector)
        if apply_button and not apply_button.is_disabled():
            apply_button.click()
            print("Apply button clicked.")
        else:
            print("Apply button is disabled or not found.")

        # Wait for the dropdown to become visible after clicking the Apply button
        page.wait_for_timeout(2000)  # Wait a moment for the UI to settle

        # Open the dropdown for meetings per page
        meetings_per_page_button = page.query_selector('button:has-text("1–10")')
        if meetings_per_page_button:
            meetings_per_page_button.click()  # Click to open the dropdown
            print("Opened the dropdown for meetings per page.")

            # Wait for the button for "100" meetings per page to be visible
            page.wait_for_selector('button.t-item:has-text("100")', timeout=10000)
            
            # Click the "100" button to select it
            option_button = page.query_selector('button.t-item:has-text("100")')
            if option_button:
                option_button.click()
                print("Set meetings per page to 100.")
            else:
                print("100 meetings per page option not found.")
        else:
            print("Meetings per page dropdown button not found.")

        # Wait for the total number of pages to be visible
        page.wait_for_selector('.t-pages', timeout=10000)

        # Extract the total number of pages
        total_pages_text = page.inner_text('.t-pages strong')
        total_pages = int(re.search(r'\d+', total_pages_text).group())
        print(f"Total pages to scrape: {total_pages}")

        # Iterate through each page
        for page_number in range(1, total_pages + 1):
            print(f"Scraping page {page_number}...")
            fetch_page_data(page, page_number)

            # Iterate through rows to find hrefs only in the "Company Name" column
            rows = page.query_selector_all('table tr')
            for row in rows:
                cells = row.query_selector_all('td')
                if cells:
                    # Check if the first cell corresponds to "Company Name"
                    company_name_cell = cells[0]  # Adjust index based on your table structure
                    link = company_name_cell.query_selector('a')
                    if link:
                        href = link.get_attribute('href')
                        if href and href not in visited_links:
                            visited_links.add(href)  # Mark this link as visited
                            meeting_link = f"https://votedisclosure.glasslewis.com{href}"  # Complete the href
                            fetch_meeting_data(browser, meeting_link, visit_number)  # Fetch data in a new tab
                            visit_number += 1
                    else:
                        print("No link found in the Company Name cell.")

            # Handle pagination
            handle_pagination(page, page_number, total_pages)

        # Close the browser
        browser.close()


if __name__ == "__main__":
    # Prompt user for input
    start_date = input("Enter start date (MM.DD.YYYY): ")
    end_date = input("Enter end date (MM.DD.YYYY): ")
    
    # Call the scraper with the input dates
    scrape_votedisclosure(start_date, end_date)
