# wjx_refactoring
### Thanks to [Zemelee/wjx](https://github.com/Zemelee/wjx) project inspiration.
Modified for headless Ubuntu environment.<br>Independent config file.<br>separate control of page duration.<br>The project is still in <b>beta testing</b>.<br>
## How to start
#### 1. Install python.  
#### 2. Install python dependency libraries: requests, numpy, selenium.
```
pip install xxx
```
#### 3. Configure Chrome and Chrome Driver, there are tutorials on the web.  
i.Windows only needs to put Chromedriver in the python home directory.<br>ii.For Linux, please refer to this [article](https://blog.csdn.net/h1773655323/article/details/132494946)
#### 4. How it works  
i. For Windows, click to run.  
ii. For Linux,  
```
python3 wjx.py
```
#### 5.What is the config.json here?  
The first half is some parameter settings for answering questions, and the second half is the question type parameters.<br> I wrote a beta version of the parameter configurator, which can be configured simply.<br>The question type parameters are the same as those of [Zemelee/wjx](https://github.com/Zemelee/wjx)，thanks again.<br>Project link [charowhite/wjx_setting](https://github.com/charowhite/wjx_setting)
```
{
    "url": "https://www.wjx.cn/vm/xxxxxx.aspx#",
    "targetCount": 2,
    "topFail": 5,
    "thread_count": 2,
    "useIp": false,
    "ip_api": "",
    "page_delay": 30,

    "single_prob": {
    },

    "droplist_prob": {
    },

    "multiple_prob": {
    },

    "matrix_prob": {
    },

    "scale_prob": {
    },

    "texts": {
    },

    "texts_prob": {
    }
}
```
## Special thanks
### [Zemelee/wjx](https://github.com/Zemelee/wjx)
