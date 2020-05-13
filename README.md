[![Build Status](https://travis-ci.org/kahinton/knotty.svg?branch=master)](https://travis-ci.org/kahinton/knotty)


[![codecov](https://codecov.io/gh/kahinton/knotty/branch/master/graph/badge.svg)](https://codecov.io/gh/kahinton/knotty)



### Welcome to Knotty, the easiest way to tie down your application performance metrics!

NOTE: While all the basic functionality is here, Knotty is still in Alpha development. The project aims to have
more libraries automatically tracked, as well as more export options. APIs and functionality are also apt to 
change with little to no warning.

Modern applications require close monitoring, and Knotty aims to provide everything you need out of the box.
Importing the library will automatically register numerous metrics regarding the performance of the application
and the system it is operating on, including hardware utilization, application logging rates, http request rates,
and many more. Beyond the build in metrics, there is also an extremely powerful meters API that allows you to 
create whatever custom metrics you would like. 

Once you have your meters defined, Knotty also provides a simple API for exporting your metrics to a number of 
commonly used metrics backends (Prometheus, InfluxDB, Graphite, etc). 

Here's a simple example of how you can add a Prometheus endpoint to a Flask application:

```python
from flask import Flask
from knotty.exporters import PrometheusExporter


app = Flask(__name__)
PrometheusExporter(flask_app=app)

@app.route('/hello', allowed_methods=['GET'])
def hello()
    return 'Hello World'
    

app.run()
```