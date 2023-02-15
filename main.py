import os
import openai
import httpx
import json
import time
from random import randint
from typing import Optional, Union, Literal

from graphql import GraphQL
from enums import Operations, ContactMethod
from exceptions import FailedAPIRequest, MaximumResults, InvalidContactMethod

graphql = GraphQL()
openai.api_key = os.getenv("openai_apikey")

try:
  config = json.loads(open("config.json", "r").read())
except FileNotFoundError:
  raise FileNotFoundError("config.json does not exist, couldn't continue.")

class Automator(object):
  """
  A class for Replit bounties, searching, fetching or applying for them.
  """
  API_URL = "https://replit.com/graphql"
  def __init__(self, cookie: str = None):
    self.cookie = cookie
    self.client = httpx.Client(headers={
      "Content-Type": "application/json",
      "Cookie": f"connect.sid={cookie if cookie else os.getenv('cookie')};",
      "Origin": "https://replit.com",
      "Referer": "https://replit.com/bounties?status=open&order=creationDateDescending",
      "Sec-fetch-dest": "empty",
      "Sec-fetch-mode": "cors",
      "Sec-fetch-site": "same-origin",
      "Sec-gpc": "1",
      "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
      "X-Client-Version": str(randint(1000000, 9999999)),
      "X-Requested-With": "XMLHttpRequest"
    })
    
  def get_open_bounties(
    self, 
    after: Optional[str] = None,
    search_query: Optional[str] = None
  ) -> Union[list, None]:
    """
    Gets all "OPEN" Replit bounties, returns list, requires:
        - after (Optional[str]): An optional string containing the after key to search for.
        - search_query (Optional[str]): An optional string for search query.
    Returns a list or None.
    """
    variables = {
      "input": {
        "count": 10,
        "listingState": "listed",
        "order": "creationDateDescending",
        "searchQuery": str(search_query) if search_query else "",
        "statuses": ["open"]
      }
    }

    if after is not None:
      variables["input"]["after"] = str(after)
    
    body = [
      {
        "operationName": Operations.SEARCH_BOUNTIES.value,
        "query": graphql.bounties_search(),
        "variables": variables
      }
    ]

    self.client.headers["Content-Type"] = "application/json"
    self.client.headers["Content-Length"] = str(len(json.dumps(body)))
    
    response = self.client.post(self.API_URL, json=body)

    if response.status_code == 200:
      data = response.json()[0]["data"]["bountySearch"]["items"]
      if len(data) > 0:
        return response.json()[0]["data"]["bountySearch"]["items"]
      else:
        raise MaximumResults("Failed to fetch bounties, maximum results")
    raise FailedAPIRequest(f"Failed to fetch bounties with status code: {response.status_code}.")

  def get_bounty_page(
    self,
    bounty_slug: str,
    username: str
  ) -> Union[dict, None]:
    """
    Returns more information regarding a Replit bounty. Requires:
        - bounty_slug (str): The slug of the bounty, can be found in response or the bounty's url.
        - username (str): The username of the creator of the bounty.
    Returns a dictionary or None. 
    """
    variables = {
      "input": {
        "slug": bounty_slug,
        "username": username
      }
    }

    body = [
      {
        "operationName": Operations.BOUNTY_PAGE.value,
        "query": graphql.bounty_page(),
        "variables": variables
      }
    ]

    self.client.headers["Content-Type"] = "application/json"
    self.client.headers["Content-Length"] = str(len(json.dumps(body)))

    response = self.client.post(self.API_URL, json=body)

    if response.status_code == 200:
      return response.json()[0]["data"]["bountyByUrl"]
    raise FailedAPIRequest(f"Failed to fetch information for bounty, status code: {response.status_code}")

  def apply_for_bounty(
    self,
    contact_method: Literal[ContactMethod.EMAIL, ContactMethod.DISCORD],
    bounty_id: int,
    application: str
  ) -> Union[bool, None]:
    """
    Applies for a Replit bounty, requires information:
        - contact_method (ContactMethod): An enum of ContactMethod, either email or discord.
        - bounty_id (int): The ID of the bounty to apply for.
        - application (str): The application to include, or the content.
    Returns a boolean value or None.
    """
    variables = {
      "input": {
        "bountyId": int(bounty_id),
        "content": application
      }
    }

    if contact_method == ContactMethod.EMAIL:
      variables["input"]["contactInfo"] = config["contact_email"]
    elif contact_method == ContactMethod.DISCORD:
      variables["input"]["contactInfo"] = config["contact_discord"]
    else:
      raise InvalidContactMethod("Invalid contact method or not supported yet.")

    body = [
      {
        "operationName": Operations.CREATE_APPLICATION.value,
        "query": graphql.create_application(),
        "variables": variables
      }
    ]

    
    self.client.headers["Content-Type"] = "application/json"
    self.client.headers["Content-Length"] = str(len(json.dumps(body)))
    
    response = self.client.post(self.API_URL, json=body)

    if response.status_code == 200:
      if not "error" in response.json():
        return True
    raise FailedAPIRequest(f"Failed to apply for bounty with status code: {response.status_code}")

def applier() -> None:
  at = Automator()
  results = []
  after = 0
  while True:
    try:
      print("Scraped some bounties.")
      if after != 0:
        response = at.get_open_bounties(after=str(after))
      else:
        response = at.get_open_bounties()
      results.append(response)
      after += 10
    except MaximumResults:
      print("Reached maximum results.")
      break
    except FailedAPIRequest as err:
      raise FailedAPIRequest(repr(err))
  for bounties in results:
    for bounty in bounties:
      information = at.get_bounty_page(
        bounty["slug"], 
        bounty["user"]["username"]
      )
      if information["hasCurrentUserApplied"] == False:
        try:
          response = openai.Completion.create(model="text-davinci-003", prompt=str(randint(1000, 9999)) + " " + config["gpt_prompt"].replace('[Project Name]', bounty['title']), temperature=0.7, max_tokens=300)
        except:
          raise Exception("Error whilst generating application.")
        decoded = response["choices"][0]["text"]
        applied = at.apply_for_bounty(
          ContactMethod.EMAIL if information["contactMethod"] == "email" else ContactMethod.DISCORD,
          bounty["id"],
          decoded
        )
        if applied == True:
          print(f"Applied successfully to {information['title']}, message: {decoded}")
        else:
          print("Failed to apply.")
      else:
        pass
  

if __name__ == "__main__":
  applier()