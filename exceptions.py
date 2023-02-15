class FailedAPIRequest(Exception):
  """
  An API request to Replit failed or didn't return the correct information.
  """
  pass

class MaximumResults(Exception):
  """
  Maximum results were reached.
  """
  pass

class InvalidContactMethod(Exception):
  """
  The contact method supplied was invalid or not supported.
  """
  pass