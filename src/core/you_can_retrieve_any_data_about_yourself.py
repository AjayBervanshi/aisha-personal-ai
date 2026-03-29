from bot import get_instagram_token, post_on_instagram
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run(request: str) -> dict:
    """
    This function retrieves data about itself and returns it as a dictionary.
    It checks if the request is from Ajay and if so, it provides the Instagram token and other data required to post on Instagram.
    
    Args:
        request (str): The request string containing the name of the person making the request.
    
    Returns:
        dict: A dictionary containing the data about itself.
    """
    try:
        if request.lower() == "ajay":
            data = {
                "instagram_token": get_instagram_token(),
                "post_data": post_on_instagram()
            }
            return data
        else:
            logging.warning("Request not from Ajay, returning empty dictionary")
            return {}
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    request = "Ajay"
    print(json.dumps(run(request), indent=4))
    request = "Other"
    print(json.dumps(run(request), indent=4))