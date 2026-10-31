import os
import requests
import pandas as pd

class ETLTools:

    def __init__(self):
        pass

    
    def extract_load(self, url: str, output_folder: str, format: str):
        """
        Extract paginated API data and save it as CSV, JSON, or Parquet.
        Supports APIs returning either a list or a dictionary with results/next.
        """
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )
        output_folder = os.path.join(project_root, output_folder)
        output_format = format.lower().strip()

        if output_format not in ("csv", "json", "parquet"):
            return f"Unsupported format: {format}"

        try:
            all_records = []
            next_url = url

            with requests.Session() as session:
                while next_url:
                    response = session.get(next_url, timeout=30)
                    response.raise_for_status()
                    data = response.json()

                    if isinstance(data, dict):
                        results = data.get("results")

                        if isinstance(results, list):
                            all_records.extend(results)
                            next_url = data.get("next")
                        else:
                            # Non-paginated JSON object
                            all_records.append(data)
                            next_url = None

                    elif isinstance(data, list):
                        all_records.extend(data)
                        next_url = None

                    else:
                        return "Unsupported API response: expected a JSON object or list."

            if not all_records:
                return "No records found in the API response."

            df = pd.json_normalize(all_records)

            os.makedirs(output_folder, exist_ok=True)
            filename = os.path.join(
                output_folder, f"extracted_data.{output_format}"
            )

            if output_format == "csv":
                df.to_csv(filename, index=False)
            elif output_format == "json":
                df.to_json(
                    filename, orient="records", lines=True, force_ascii=False
                )
            else:
                df.to_parquet(filename, index=False)

            return (
                f"Data successfully extracted and saved to {filename}. "
                f"Records: {len(df)}, Columns: {len(df.columns)}"
            )

        except requests.exceptions.RequestException as e:
            return f"Failed to extract data: {e}"
        except (ValueError, TypeError) as e:
            return f"Failed to process API response: {e}"
        except Exception as e:
            return f"Failed to save extracted data: {e}"


    def transform_load_context(self, file_path:str):
        """
        This tool transforms the data from the specified file and loads it into the
        desired location (output_folder).

        Args:
            file_path (str): The path to the file containing the data to be transformed.
            output_folder (str): The folder where the transformed data will be saved.
            output_format (str): The format in which to save the transformed data (csv, json, parquet).
        Returns:
            str: A message indicating the success or failure of the operation.
        """

        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension == ".csv":
            df = pd.read_csv(file_path)
        elif file_extension == ".json":
            df = pd.read_json(file_path, lines=True)
        elif file_extension == ".parquet":
            df = pd.read_parquet(file_path)
        else:
            return f"Unsupported file format: {file_extension}"

        top_3_rows = str(df.head(3))

        return top_3_rows


    def execute_code(self,code:str):
        """
        This tool executes the provided code and returns the output.

        Args:
            code (str): The code to be executed.
        Returns:
            str: The output of the executed code or an error message if execution fails.
        """

        try:
            exec(code)
            return "Code executed successfully."
        except Exception as e:
            return f"Failed to execute code: {e}"


if __name__ == "__main__":
    obj = ETLTools()
    path = "C:\\Data_Agent\\data\\extract\\extracted_data.csv"
    print(obj.transform_load_context(path))
          