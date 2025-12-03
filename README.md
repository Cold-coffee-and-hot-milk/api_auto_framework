
# api_auto_framework
接口自动化测试框架
=======
本接口自动化框架已实现从测试用例中自动提取接口请求信息，并自动发送请求，返回响应结果。
按此框架进行接口测试，仅需在/data/test_cases模块内存放按规定格式写好的测试用例即可。

测试用例格式说明：
1.必须是yaml文件格式，即以.yaml结尾的文件。
2.文件内格式也要按发送请求的数据格式进行响应的调整。

本接口自动化框架已实现从测试用例中自动提取接口请求信息，并自动发送请求，返回响应结果。

按此框架进行接口自动化测试时，仅需在/data/test_cases目录内存放按规定格式写好的测试用例即可。

**测试用例格式说明**：

1.必须是yaml文件格式，即以.yaml结尾的文件。

2.测试用例存放位置必须是/data/test_cases目录下（可在其目录内在创建新文件夹存储）。

3.测试用例内的数据信息格式必须按模版格式保持相同的缩进。





**特殊场景**：

​		如当前请求接口需要依赖某个接口的返回数据时，需将依赖接口放在当前接口前面执行，并按照对应格式将依赖接口返回的响应数据提取出来，当前接口按格式进行一个参数化即可。格式如下：

接口响应数据如下图：

<img src="/Users/xiejr/Library/Application Support/typora-user-images/image-20251113192447560.png" alt="image-20251113192447560" style="zoom:50%;" />

​		现要提取user_uniquecode、x_Auth_Token两个数据，为方便记忆，存储数据的变量名尽可能与当前接口所需字段名（X-Auth-Code、x_Auth_Token）保持一致。

需在测试用例内按下面格式书写：

```python
  extract:
    X-Auth-Code: jsonpath:$.data[0].user_uniquecode
    x_Auth_Token: jsonpath:$.data[0].x_Auth_Token
```

**注意**：extract需与request保持相同的缩进格式。

在当前接口中引用变量时应按照下面格式书写：

```python
data:
  X-Auth-Code: "${X-Auth-Code}"
  x_Auth_Token: "${x_Auth_Token}"
```




