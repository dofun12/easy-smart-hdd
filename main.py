import re

import pandas
import pandas as pd
import subprocess

def fix_parts(parts):
    if len(parts) <= 10:
        return parts
    value = ' '.join(parts[9:])
    new_parts = parts[:9]
    new_parts.append(value)
    return new_parts


def parse_smart_attributes_data(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    attributes_section = False
    attributes_data = []

    for line in lines:
        if "Vendor Specific SMART Attributes with Thresholds:" in line:
            attributes_section = True
            continue
        if attributes_section:
            if line.strip() == "" or line.startswith(r"[0-9]"):
                attributes_data.append(line.strip())
                continue
            if line.startswith("SMART Error Log Version:"):
                break
            attributes_data.append(line.strip())

    # Parse the attributes data
    attributes = []
    for data in attributes_data:

        data = data.replace(r' ', ';')
        data = re.sub(r';{2,}', ';', data)
        parts = re.split(';', data)
        print(parts)
        parts = fix_parts(parts)
        if len(parts) < 9:
            continue
        attributes.append(parts)

    # Create a pandas DataFrame
    columns = ["ID#", "ATTRIBUTE_NAME", "FLAG", "VALUE", "WORST", "THRESH", "TYPE", "UPDATED", "WHEN_FAILED", "RAW_VALUE"]
    df = pd.DataFrame(attributes, columns=columns)
    return df


def parse_smart_output(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    errors = []
    self_tests = []
    selective_tests = []
    smart_revision = None

    error_pattern = re.compile(r'Error (\d+) occurred at disk power-on lifetime: (\d+) hours')
    self_test_pattern = re.compile(r'#\s+(\d+)\s+(\w+ \w+)\s+(\w+):\s+(\w+ \w+)\s+(\d+)%\s+(\d+)\s+(-|\d+)')
    selective_test_pattern = re.compile(r'\s+(\d+)\s+(\d+)\s+(\d+)\s+(\w+)')
    revision_pattern = re.compile(r'SMART Attributes Data Structure revision number:\s+(\d+)')

    current_section = None

    for line in lines:
        if 'Error' in line:
            current_section = 'errors'
            match = error_pattern.search(line)
            if match:
                error_id, lifetime = match.groups()
                errors.append({'error_id': error_id, 'lifetime': lifetime})
        elif 'SMART Self-test log structure revision number' in line:
            current_section = 'self_tests'
        elif 'SMART Selective self-test log data structure revision number' in line:
            current_section = 'selective_tests'
        elif current_section == 'self_tests':
            match = self_test_pattern.search(line)
            if match:
                self_tests.append(match.groups())
        elif current_section == 'selective_tests':
            match = selective_test_pattern.search(line)
            if match:
                selective_tests.append(match.groups())
        else:
            match = revision_pattern.search(line)
            if match:
                smart_revision = match.group(1)

    return errors, self_tests, selective_tests, smart_revision


def display_smart_info(errors, self_tests, selective_tests, smart_revision):
    print("SMART Attributes Data Structure revision number:", smart_revision)

    print("\nSMART Errors:")
    for error in errors:
        print(f"Error ID: {error['error_id']}, Lifetime: {error['lifetime']} hours")

    print("\nSMART Self-tests:")
    for test in self_tests:
        print(
            f"Test #{test[0]}: {test[1]}, Status: {test[2]}, Remaining: {test[4]}%, Lifetime: {test[5]} hours, LBA of first error: {test[6]}")

    print("\nSMART Selective Self-tests:")
    for test in selective_tests:
        print(f"Span: {test[0]}, Min LBA: {test[1]}, Max LBA: {test[2]}, Status: {test[3]}")


if __name__ == '__main__':
    subprocess.run(['smartctl', '-a', '/dev/sda'], stdout=open('disk_usage.txt', 'w'))

    errors, self_tests, selective_tests, smart_revision = parse_smart_output('disk_usage.txt')
    display_smart_info(errors, self_tests, selective_tests, smart_revision)
    result_df: pandas.DataFrame = parse_smart_attributes_data('disk_usage.txt')
    #print(result_df)

    result_query = result_df.query('VALUE < THRESH')
    print(result_query)

