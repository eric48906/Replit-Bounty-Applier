from enum import Enum

class Operations(Enum):
  SEARCH_BOUNTIES = "BountiesPageSearch"
  BOUNTY_PAGE = "BountyPage"
  CREATE_APPLICATION = "CreateApplication"

class ContactMethod(Enum):
  EMAIL = 1
  DISCORD = 2