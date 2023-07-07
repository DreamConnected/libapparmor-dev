#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/printk.h>

int init_module(void)
{
	printk(KERN_INFO "apparmor: loaded module_test\n");
	return 0;
}

void cleanup_module(void)
{
	printk(KERN_INFO "apparmor: unloaded module_test\n");
}

MODULE_LICENSE("GPL");
