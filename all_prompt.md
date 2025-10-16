tmp\poco_v1 使用 uiautomator1 旧版本的 poco. ./Poco 使用新版本 uiautomator2 的poco 但是兼容了两种模式并且设计上可能有缺陷或者因需要接合别的项目有不必要的代码, 因此只能作为参考, 我现在希望的是tmp\poco_v1 只兼容 uiautomator2 并且返回数据方式与原始相同, 方便 airtest 集成 poco toolkit

uiautomator 不支持在视频播放状态获取 xml(poco 底层使用它因此也无法工作). uiautomator2 能获取, 
可能遇到问题：

poco dump 元素在 mobile 似乎有些问题, 导致自动小屏, 获取不到播放页(暂停播放状态元素). 考虑到兼容问题, 完全使用 uiautomator2 获取元素, 并采用 poco 计算 pos 的方法用于传递参数

Poco的dump逻辑存在bug，原始XML包含完整package信息，但经过Poco处理后package统计为空{} UIAutomator2 可正确提取95个com.unitvnet.mobs节点，但Poco层丢失了所有package信息
请你尝试修复 Poco的问题, 让 Poco 使用 UIAutomator2 新方式进行 元素处理, 比如当我 Click 时 使用新的方式以避免版本混用导致的冲突

1.在开始前 我需要你了解 uiautomator1 uiautomator2 区别, 列好注意事项, 如果
2.在开始前写一个测试脚本, 虚拟调用 uiautomator1 的 函数返回, 涉及主要分支即可/ 比如输出/操作返回(你可以尽情 mock 数据, 只需要最后把 mock 去掉即可), 这个将用于验证你成功改写  tmp\poco_v1 为 uiautomator2 是否成功

"Act as an Expert Python Refactoring and Android Automation Engineer.

My primary goal is to overhaul the existing tmp\poco_v1 codebase to exclusively utilize UIAutomator2 while maintaining a backward-compatible data return structure for seamless integration with the Airtest Poco toolkit.

You are tasked with the following:

Phase 1: Analysis and Setup

UIAutomator Comparison: Provide a concise summary of the key technical differences and compatibility cautions between UIAutomator1 and UIAutomator2 relevant to element fetching and XML dumping.

mention: the poco has own method to convert UIAutomator  data to poco data(it's has own algrothem) you ned compati it using UIAutomator2 

Verification Script: Draft a Python test script that mocks the primary output/return values of UIAutomator1 functions used for element fetching (e.g., dump() or equivalent calls). This script will be used later to ensure that, post-refactor, the UIAutomator2 implementation correctly handles and transforms its data into the expected output format of the older version.

Phase 2: Code Refactoring and Bug Fixes

Assume you are working directly on the tmp\poco_v1 source code. Modify the code to address the following issues by switching entirely to UIAutomator2's methods:

UIAutomator2 Exclusive Use: Ensure all low-level element retrieval, XML dumping, and interaction logic (like Click) now only call UIAutomator2 APIs. The reference implementation in ./Poco may be consulted for structure but do not include any unnecessary code from it.

Fix Element Dumping Bug: Correct the Poco layer's logic so that complete package information (and all other necessary XML data) is preserved from the UIAutomator2 XML output and passed correctly to the upper layers. The issue where package statistics are lost (e.g., package statistics: {} instead of valid data) must be fixed.

Address Video/Display Issues: Implement the UIAutomator2 element fetching mechanism in a way that resolves issues like the inability to capture elements during video playback and screen shrinking during the dump process. Poco should only be used for necessary post-processing, such as position calculation.



/Poco 是之前的示例代码, 这个过程不应该对他进行任何改动的, 需要改动的是 tmp/poco_v1 我会在你改完后复制为  C:\Download\AirtestIDE-win-1.2.17\AirtestIDE\poco  (这是原来的读取方式) 以此让airtest 使用新版本 poco with uiautomator2 , 如果你并非按我设想的做的, 请你反思

很好, 已经完美解决了, 将最近遇到的问题反思, 写入 docs/*md 写入最近遇到的问题, 为何多次未修复, 最后如何修复成功, 你的经验之谈, 避免emoji, 书写要精简, 不要无用废话, 足够熟悉则能看懂,


---


▌现在需要拟解决一个新的问题, 我发现目前进行 poco 定位控件时 其有定位漂移, 比如 实际坐标是 0.906,0.529 但是 只有我框到 0.904,0.529 时才显示这个控件 这是返回的坐标信息,  你需要对比 原始 XML 信息 和 计算出的, 是
▌否一致, 是什么导致了 定位的 位置整体向下偏移,
▌Path from root node: [0, 2, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1]
▌Payload details:
▌         type :  android.widget.TextView
▌         name :  See all
▌         text :  See all
▌         enabled :  True
▌         visible :  True
▌         pos :  [0.9017361111111111, 0.5311347808275297]
▌         size :  [0.11597222222222223, 0.029905776321179845]
▌         scale :  [1.0, 1.0]
▌         anchorPoint :  [0.5, 0.5]
▌         zOrders :  {'local': 0, 'global': 0}
▌         resourceId :  b'com.mobile.brasiltvmobile:id/mTvMore'
▌         package :  b'com.mobile.brasiltvmobile'
▌         contentDesc :  b''
▌         class_name :  b'android.widget.TextView'
▌         clickable :  True
▌         touchable :  True
▌         focusable :  True
▌         focused :  False
▌         scrollable :  False
▌         selected :  False
▌         checkable :  False
▌         checked :  False
▌         longClickable :  False
▌         editable :  False
▌         dismissable :  False
▌         bounds :  [0.84375, 0.5161818926669398, 0.9597222222222223, 0.5460876689881197]
▌         boundsInParent :  [0.11597222222222223, 0.029905776321179845]


----

你确定代码已同步吗, 大部分控件still 偏移的, 特别是 屏幕的中下部分控件, 检查下 poco 原来是怎么做的, 为什么其正常 "C:\Download\AirtestIDE-win-1.2.17\AirtestIDE\poco_old" 是我备份的老代码, 需要使用时查看他, 但不要对其做任何更改

*---

确实成功加载出正确的位置了, 但是我想问你, 你没有使用原始 poco 方式 对吗, 因为我发现其无法检测到播放状态的控件了, 全屏下理论有很多控件的 之前也能检测到 只是有些偏移, 现在一个都检测不到了, 我使用 uiautomator2 就是为了它 但是现在不支持?
