# lambda function to subscribe a new query
from .lambda_handlers import lambda_handler_subscribe
from .lambda_handlers import lambda_handler_confirm_subscription
from .lambda_handlers import lambda_handler_unsubscribe

lambda_handler = lambda_handler_subscribe




