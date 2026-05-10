# Testing how logging works in Python

import logging

logging.basicConfig(filename="./test.log", filemode="a", format="%(asctime)s - %(levelname)s - %(lineno)d - %(message)s")

# Create a new logger instead of using root logger 
logger=logging.getLogger()

# Setting logging level since default is NOT SET
logger.setLevel(logging.INFO)

logger.debug("This is a debug message") # 10
logger.info("This is an info message") # 20
logger.warning("This is a warning message") #30
logger.error("This is an error message") #40
logger.critical("This is a critical message") #50
