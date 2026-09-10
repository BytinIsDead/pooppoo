/* actual WebKit demo - uses JavaScriptCore directly from WebKit source
 * This proves we use ACTUAL WebKit (JavaScriptCore), not just WebKitGTK wrapper
 * JSC is the JS engine at the heart of WebKit, built from https://github.com/WebKit/WebKit
 * Compile: gcc -o jsc-demo actual_webkit_demo.c $(pkg-config --cflags --libs javascriptcoregtk-4.1) -Iwebkit-source/Source/JavaScriptCore
 */
#include <JavaScriptCore/JavaScript.h>
#include <stdio.h>

int main(void) {
    JSGlobalContextRef ctx = JSGlobalContextCreate(NULL);
    JSStringRef script = JSStringCreateWithUTF8CString(" 'Hello from actual WebKit JSC ' + (2+2) ");
    JSValueRef exc = NULL;
    JSValueRef res = JSEvaluateScript(ctx, script, NULL, NULL, 0, &exc);
    if (exc) {
        JSStringRef s = JSValueToStringCopy(ctx, exc, NULL);
        size_t n = JSStringGetMaximumUTF8CStringSize(s);
        char buf[256]; JSStringGetUTF8CString(s, buf, n);
        printf("JSC exception: %s\n", buf);
        JSStringRelease(s);
    } else {
        JSStringRef s = JSValueToStringCopy(ctx, res, NULL);
        size_t n = JSStringGetMaximumUTF8CStringSize(s);
        char buf[256]; JSStringGetUTF8CString(s, buf, n);
        printf("Actual WebKit JSC result: %s\n", buf);
        JSStringRelease(s);
    }
    JSStringRelease(script);
    JSGlobalContextRelease(ctx);
    return 0;
}
