# agora-python
Python library for the Agora Protocol.

The Agora Protocol is a protocol for efficient communication between heterogeneous agents. It allows agents of any framework to communicate with agents in any other framework, while maximizing efficiency.

## Installation

```
pip install agora-protocol
```

## Usage

There are two ways to use Agora: as a sender agent (i.e. a client) or as a receiver agent (i.e. a server). An agent can also act as both a sender and a receiver.

This is a quick example where two agents (a LangChain agent and a Camel agent) exchange weather data.

### Sender

```python
import agora
from langchain_openai import ChatOpenAI # Needs to be installed separately

model = ChatOpenAI(model="gpt-4o-mini")
toolformer = agora.toolformers.LangChainToolformer(model)

sender = agora.Sender.make_default(toolformer)

# Any properly annotated function with Google-style docstrings
# can be automatically converted to a task. Refer to the documentation for other ways
# to describe tasks
@sender.task()
def get_temperature(city : str) -> int:
  """
  Get the temperature for a given city.

  Parameters:
    city: The name of the city for which to retrieve the weather

  Returns:
    The temperature in °C for the given city.
  """
  pass


response = get_temperature('New York', target='http://localhost:5000')
print(response) # Output: 25
```

### Receiver

```python
import agora
import camel.types # Needs to be installed separately

toolformer = agora.toolformers.CamelToolformer(
  camel.types.ModelPlatformType.OPENAI,
  camel.types.ModelType.GPT_4O
)


def weather_db(city: str) -> dict:
  """Gets the temperature and precipitation in a city.
  
  Args:
    city: The name of the city for which to retrieve the weather
  
  Returns:
    A dictionary containing the temperature and precipitation in the city (both ints)

  """
  # Put your tool logic here
  return {
    'temperature': 25,
    'precipitation': 12
  }


receiver = agora.Receiver.make_default(toolformer, tools=[weather_db])

server = agora.ReceiverServer(receiver)
server.run(port=5000)
```

## Contributing

If you want to contribute, join our [Discord](https://discord.gg/MXmfhwQ4FB) to find out more!
