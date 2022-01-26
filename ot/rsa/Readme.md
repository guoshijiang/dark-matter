### Rsa 项目说明

Python 中基于 RSA 的 k-out-of-n 不经意传输 (OT)。

当您有两方 Alice 和 Bob 时使用 OT。爱丽丝有 n 秘密，并想在 k 不泄露任何其他秘密的情况下与鲍勃分享。Bob 想要挑选大小为 的 Alice 秘密的某个子集 k，但不想向 Alice 透露 k 他挑选了哪些秘密。OT 可以用来解决这个问题，让爱丽丝“不经意间”将 k 秘密转移给鲍勃。

### 代码解释

ot 下的 RSA 提供两个类，Alice 和 Bob。对于这个例子，假设 Alice 有 3 个秘密，Secret message 1、Secret message 2和 Secret message 3，并且 Bob 将抓住其中的两个（3 个 OT 中的 2 个）。
在 Alice 的终端上：

```buildoutcfg
 from ot import *
 secrets = [b'Secret message 1', b'Secret message 2', b'Secret message 3']
 alice = Alice(secrets, 2, len(secrets[0]))
```

我们现在可以setup在Alice对象上运行，这将开始 OT。默认情况下，它将 json 写入一个名为alice_setup.json.

```
alice.setup()
Pubkey and hashes published.
```

现在切换到 Bob 的终端。为了创建一个Bob对象，我们传递 Alice 拥有的消息数量、所需消息的数量以及我们想要的消息 ID 列表。假设我们想要 Alice 拥有的第一个和第三个秘密：

```buildoutcfg
from ot import *
bob = Bob([0, 2])
bob.setup()
Polynomial published.
```

默认情况下，Bob.setup读取alice_setup.json和写入bob_setup.json.
现在回到 Alice 的终端：

```buildoutcfg
alice.transmit()
G has been published.
```

这默认读取bob_setup.json和写入alice_dec.json.
最后，回到 Bob 的终端：

```buildoutcfg
bob.receive()
[b'Secret message 1', b'Secret message 3']
```

默认情况下从alice_dec.json.
我们可以看到我们有我们要求的秘密。如果传输出现问题或 Alice 试图弄乱一些东西（即哈希不匹配），我们将得到如下信息：

```buildoutcfg
bob.receive()
Hashes don't match. Either something messed up or Alice is up to something.
[b'messed up secret here']
```




