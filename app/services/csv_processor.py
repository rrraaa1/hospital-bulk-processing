"""
CSV validation and processing service
"""

import csv
import io
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class CSVProcessor:
    """Handles CSV validation and parsing"""

    REQUIRED_COLUMNS = ['name', 'address']
    OPTIONAL_COLUMNS = ['phone']

    def validate_csv(self, content: bytes) -> Dict[str, Any]:
        """
        Validate CSV format and content

        Args:
            content: Raw CSV file content as bytes

        Returns:
            Dictionary with validation results
        """
        errors = []
        warnings = []
        total_rows = 0

        try:
            # Decode content
            text_content = content.decode('utf-8-sig')  # Handle BOM

            # Parse CSV
            reader = csv.DictReader(io.StringIO(text_content))

            # Check if file is empty
            if not reader.fieldnames:
                errors.append("CSV file is empty or has no headers")
                return {
                    'is_valid': False,
                    'total_rows': 0,
                    'errors': errors,
                    'warnings': warnings
                }

            # Validate headers
            headers = [h.strip().lower() for h in reader.fieldnames]

            # Check required columns
            missing_columns = [col for col in self.REQUIRED_COLUMNS if col not in headers]
            if missing_columns:
                errors.append(f"Missing required columns: {', '.join(missing_columns)}")

            # Check for unknown columns
            known_columns = self.REQUIRED_COLUMNS + self.OPTIONAL_COLUMNS
            unknown_columns = [col for col in headers if col not in known_columns]
            if unknown_columns:
                warnings.append(f"Unknown columns will be ignored: {', '.join(unknown_columns)}")

            # Validate rows
            row_errors = []
            for idx, row in enumerate(reader, start=1):
                total_rows += 1

                # Check required fields
                name = row.get('name', '').strip() if 'name' in row else ''
                address = row.get('address', '').strip() if 'address' in row else ''

                if not name:
                    row_errors.append(f"Row {idx}: Missing or empty 'name' field")

                if not address:
                    row_errors.append(f"Row {idx}: Missing or empty 'address' field")

                # Validate name length
                if name and len(name) > 200:
                    row_errors.append(f"Row {idx}: Hospital name exceeds 200 characters")

                # Validate address length
                if address and len(address) > 500:
                    row_errors.append(f"Row {idx}: Address exceeds 500 characters")

                # Validate phone if provided
                phone = row.get('phone', '').strip() if 'phone' in row else ''
                if phone and len(phone) > 20:
                    row_errors.append(f"Row {idx}: Phone number exceeds 20 characters")

            # Add row-specific errors
            if row_errors:
                # Limit error messages to first 10
                if len(row_errors) > 10:
                    errors.extend(row_errors[:10])
                    errors.append(f"... and {len(row_errors) - 10} more row errors")
                else:
                    errors.extend(row_errors)

            # Check if file has data
            if total_rows == 0:
                errors.append("CSV file contains no data rows")

            # Determine if valid
            is_valid = len(errors) == 0

            logger.info(
                f"CSV validation completed. Valid: {is_valid}, "
                f"Rows: {total_rows}, Errors: {len(errors)}"
            )

            return {
                'is_valid': is_valid,
                'total_rows': total_rows,
                'errors': errors,
                'warnings': warnings
            }

        except UnicodeDecodeError:
            errors.append("Invalid file encoding. Please use UTF-8 encoding.")
            return {
                'is_valid': False,
                'total_rows': 0,
                'errors': errors,
                'warnings': warnings
            }
        except csv.Error as e:
            errors.append(f"CSV parsing error: {str(e)}")
            return {
                'is_valid': False,
                'total_rows': 0,
                'errors': errors,
                'warnings': warnings
            }
        except Exception as e:
            logger.error(f"Unexpected validation error: {str(e)}")
            errors.append(f"Validation error: {str(e)}")
            return {
                'is_valid': False,
                'total_rows': 0,
                'errors': errors,
                'warnings': warnings
            }

    def parse_csv(self, content: bytes) -> List[Dict[str, str]]:
        """
        Parse CSV content into list of hospital dictionaries

        Args:
            content: Raw CSV file content as bytes

        Returns:
            List of hospital data dictionaries
        """
        hospitals = []

        try:
            # Decode content
            text_content = content.decode('utf-8-sig')

            # Parse CSV
            reader = csv.DictReader(io.StringIO(text_content))

            for row in reader:
                # Extract and clean data
                hospital = {
                    'name': row.get('name', '').strip(),
                    'address': row.get('address', '').strip(),
                }

                # Add phone if provided
                phone = row.get('phone', '').strip()
                if phone:
                    hospital['phone'] = phone

                hospitals.append(hospital)

            logger.info(f"Parsed {len(hospitals)} hospitals from CSV")
            return hospitals

        except Exception as e:
            logger.error(f"Error parsing CSV: {str(e)}")
            raise ValueError(f"Failed to parse CSV: {str(e)}")